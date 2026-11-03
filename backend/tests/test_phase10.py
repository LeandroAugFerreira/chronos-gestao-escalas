import importlib.util
import io
import json
from pathlib import Path
import stat
import zipfile
import pytest
from app.core.config import PROJECT_ROOT

spec=importlib.util.spec_from_file_location("chronos_package",PROJECT_ROOT/"scripts/package_release.py")
package=importlib.util.module_from_spec(spec); spec.loader.exec_module(package)


@pytest.fixture
def source(tmp_path):
    root=tmp_path/"project"; root.mkdir()
    for directory in package.SOURCE_DIRS: (root/directory).mkdir()
    for name in package.ROOT_FILES: (root/name).write_text("Chronos 1.0\n",encoding="utf-8")
    release={"product":"Chronos","official_name":package.OFFICIAL,"display_name":"Chronos 1.0","version":"1.0","phase":10,
        "package_kind":"local-review-package","release_ready":False,"published":False,"date":"2026-10-26"}
    (root/"release.json").write_bytes(package.canonical(release))
    (root/"automation/n8n").mkdir(); (root/"automation/n8n/security-status.json").write_text('{"execution_allowed":false}')
    (root/"docs/release").mkdir(); (root/"docs/release/status.json").write_text('{"production_ready":false,"pending_gates":["browser","n8n"]}')
    (root/"backend/main.py").write_text("print('Chronos 1.0')\n")
    return root


def rewrite(source, target, replacement):
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(target,"w") as changed:
        for entry in original.infolist():
            changed.writestr(entry,replacement.get(entry.filename,original.read(entry.filename)))


def test_review_archive_is_reproducible_and_excludes_runtime(source,tmp_path):
    for name in [".env","backend/live.sqlite3","backend/error.log","frontend/node_modules/private.txt","backend/credentials.json","docs/.private/key.json"]:
        path=source/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text("DO-NOT-PACK")
    first=package.build_package(source,tmp_path/"a.zip"); second=package.build_package(source,tmp_path/"b.zip")
    assert first["archive_sha256"]==second["archive_sha256"]
    assert first["verified"] and not first["release_ready"] and not first["published"]
    with zipfile.ZipFile(tmp_path/"a.zip") as archive:
        assert all(b"DO-NOT-PACK" not in archive.read(n) for n in archive.namelist())
        manifest=json.loads(archive.read(package.MANIFEST))
        assert manifest["pending_gates"]==["browser","n8n"]
        assert manifest["official_name"]==package.OFFICIAL


def test_archive_rejects_configured_secret_without_writing_output(source,tmp_path):
    value="test-only-local-release-secret-1042"
    (source/".env").write_text("CHRONOS_JWT_SECRET="+value)
    (source/"backend/main.py").write_text("secret = '"+value+"'")
    with pytest.raises(ValueError,match="Segredo local") as error: package.build_package(source,tmp_path/"leak.zip")
    assert value not in str(error.value) and not (tmp_path/"leak.zip").exists()


def test_package_never_overwrites_existing_file(source,tmp_path):
    target=tmp_path/"existing.zip"; target.write_bytes(b"USER-FILE")
    with pytest.raises(FileExistsError): package.build_package(source,target)
    assert target.read_bytes()==b"USER-FILE"


def test_creation_race_never_deletes_someone_elses_file(source,tmp_path,monkeypatch):
    target=tmp_path/"race.zip"; original=Path.open
    def raced(path,mode="r",*args,**kwargs):
        if path==target and mode=="xb":
            with original(target,"wb") as stream: stream.write(b"USER-CREATED")
        return original(path,mode,*args,**kwargs)
    monkeypatch.setattr(Path,"open",raced)
    with pytest.raises(FileExistsError): package.build_package(source,target)
    assert target.read_bytes()==b"USER-CREATED"


def test_modified_member_is_detected(source,tmp_path):
    package.build_package(source,tmp_path/"original.zip")
    rewrite(tmp_path/"original.zip",tmp_path/"tampered.zip",{package.PREFIX+"README.md":b"changed"})
    with pytest.raises(ValueError,match="Hash ou tamanho"): package.verify_package(tmp_path/"tampered.zip")


def test_internal_release_cannot_claim_ready_despite_matching_hashes(source,tmp_path):
    package.build_package(source,tmp_path/"original.zip")
    with zipfile.ZipFile(tmp_path/"original.zip") as archive:
        manifest=json.loads(archive.read(package.MANIFEST)); release=json.loads(archive.read(package.PREFIX+"release.json"))
    release["release_ready"]=True; content=package.canonical(release)
    entry=next(item for item in manifest["files"] if item["path"]=="release.json")
    entry.update(bytes=len(content),sha256=package.sha(content))
    rewrite(tmp_path/"original.zip",tmp_path/"contradictory.zip",{package.PREFIX+"release.json":content,package.MANIFEST:package.canonical(manifest)})
    with pytest.raises(ValueError,match="Metadados internos"): package.verify_package(tmp_path/"contradictory.zip")


@pytest.mark.parametrize("name",["../escape.txt","/absolute.txt","Chronos-1.0/../escape.txt","Chronos-1.0/C:/secret","Chronos-1.0/backend\\secret.py","Chronos-1.0/./README.md","Chronos-1.0/readme.md"])
def test_zip_traversal_is_rejected(source,tmp_path,name):
    package.build_package(source,tmp_path/"valid.zip")
    with zipfile.ZipFile(tmp_path/"valid.zip","a") as archive: archive.writestr(name,b"unsafe")
    with pytest.raises(ValueError): package.verify_package(tmp_path/"valid.zip")


def test_symlink_member_is_rejected(source,tmp_path):
    package.build_package(source,tmp_path/"valid.zip")
    entry=zipfile.ZipInfo(package.PREFIX+"backend/link.py"); entry.external_attr=(stat.S_IFLNK|0o777)<<16
    with zipfile.ZipFile(tmp_path/"valid.zip","a") as archive: archive.writestr(entry,b"/outside")
    with pytest.raises(ValueError): package.verify_package(tmp_path/"valid.zip")


def test_build_is_included_only_when_requested_and_available(source,tmp_path):
    with pytest.raises(ValueError,match="Execute o build"): package.build_package(source,tmp_path/"missing.zip",True)
    (source/"frontend/dist/assets").mkdir(parents=True)
    (source/"frontend/dist/index.html").write_text('<script src="/assets/main.js"></script>')
    (source/"frontend/dist/assets/main.js").write_text("console.log('Chronos')")
    package.build_package(source,tmp_path/"built.zip",True)
    with zipfile.ZipFile(tmp_path/"built.zip") as archive: assert package.PREFIX+"frontend/dist/assets/main.js" in archive.namelist()


def test_bad_identity_and_unsafe_release_claims_are_rejected(source,tmp_path):
    path=source/"release.json"; value=json.loads(path.read_text(encoding="utf-8")); value["release_ready"]=True; path.write_bytes(package.canonical(value))
    with pytest.raises(ValueError,match="Metadados"): package.build_package(source,tmp_path/"bad.zip")
    value["release_ready"]=False; value["official_name"]="Chronos corrupted"; path.write_bytes(package.canonical(value))
    with pytest.raises(ValueError,match="Metadados"): package.build_package(source,tmp_path/"bad-name.zip")


def test_packaging_limits_do_not_truncate(source,tmp_path,monkeypatch):
    monkeypatch.setattr(package,"MAX_FILES",1)
    with pytest.raises(ValueError,match="excede limites"): package.build_package(source,tmp_path/"limited.zip")
    assert not (tmp_path/"limited.zip").exists()


def test_microbenchmark_uses_same_inputs_and_does_not_claim_human_gains():
    from scripts.portfolio_benchmark import run_benchmark
    value=json.loads((PROJECT_ROOT/"data/synthetic/portfolio_benchmark.json").read_text(encoding="utf-8"))
    original=json.dumps(value,sort_keys=True)
    report=run_benchmark(value,repetitions=1)
    assert json.dumps(value,sort_keys=True)==original
    assert report["simulated"] and report["human_productivity_gain"] is None and report["human_work_time_seconds"] is None
    for case in report["cases"]:
        for policy in ["manual_simulated_policy","chronos_solver"]:
            result=case[policy]
            assert result["required_staff_minutes"]==result["covered_staff_minutes"]+result["uncovered_staff_minutes"]==1440
            assert result["constraint_error_categories"]==0
            assert result["uncovered_staff_minutes"]==(0 if case["population"]==3 else 480)
        assert case["manual_simulated_policy"]["hypothetical_cost_cents"]==case["chronos_solver"]["hypothetical_cost_cents"]
