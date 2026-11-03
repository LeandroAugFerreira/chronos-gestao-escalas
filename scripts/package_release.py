"""Chronos 1.0 — pacote local de revisão, sem instalar, executar ou publicar serviços."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "Chronos-1.0/"
MANIFEST = PREFIX + "RELEASE-MANIFEST.json"
OFFICIAL = "Chronos — Gestão Inteligente de Jornadas e Escalas"
ROOT_FILES = {".env.example", ".gitignore", "README.md", "CHANGELOG.md", "release.json", "docker-compose.yml"}
SOURCE_DIRS = {"backend", "frontend", "automation", "data", "docs", "scripts", "desktop"}
SKIP_DIRS = {"node_modules", "dist", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".vite", "coverage", "htmlcov", ".runtime", "releases"}
EXTENSIONS = {".py", ".ps1", ".json", ".md", ".ts", ".tsx", ".mjs", ".html", ".css", ".svg", ".ico", ".spec", ".woff2", ".yml", ".yaml", ".ini", ".cfg", ".toml", ".txt", ".mako"}
MAX_FILES, MAX_BYTES, MAX_FILE = 2000, 64 * 1024 * 1024, 8 * 1024 * 1024


def sha(data): return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def linked(path):
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def selected_files(root, include_build):
    for name in sorted(ROOT_FILES):
        path = root / name
        if not path.is_file(): raise ValueError("Arquivo obrigatório ausente: " + name)
        yield path
    for directory in sorted(SOURCE_DIRS):
        base = root / directory
        if not base.is_dir() or linked(base): raise ValueError("Diretório de origem inválido: " + directory)
        for folder, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
            if any(linked(Path(folder)/d) for d in dirs): raise ValueError("Junção/link de origem não permitido")
            for name in sorted(files):
                path = Path(folder)/name
                if name.startswith(".") or path.suffix.lower() not in EXTENSIONS or name.lower() in {"credentials.json", "secrets.json"}:
                    continue
                yield path
    if include_build:
        build = root/"frontend/dist"
        if not (build/"index.html").is_file() or not list((build/"assets").glob("*.js")):
            raise ValueError("Execute o build frontend antes de incluir os arquivos compilados")
        if linked(build): raise ValueError("Build não pode ser uma junção/link")
        for folder, dirs, files in os.walk(build, followlinks=False):
            if any(linked(Path(folder)/d) for d in dirs): raise ValueError("Link no build não permitido")
            for name in sorted(files):
                path=Path(folder)/name
                if path.suffix.lower() in {".html", ".js", ".css", ".svg", ".woff2"}: yield path


def configured_secrets(root):
    keys = {"CHRONOS_JWT_SECRET", "JWT_SECRET", "CHRONOS_N8N_OUTBOUND_TOKEN", "CHRONOS_BOOTSTRAP_PASSWORD"}
    values = {os.environ.get(key, "") for key in keys}
    local = root/".env"
    if local.is_file() and not linked(local):
        for line in local.read_text(encoding="utf-8-sig").splitlines():
            key, _, value = line.partition("=")
            if key.strip() in keys: values.add(value.strip().strip("\"'"))
    return [value.encode() for value in values if len(value) >= 12]


def review_metadata(root):
    release = json.loads((root/"release.json").read_text(encoding="utf-8"))
    if (release.get("official_name") != OFFICIAL or release.get("display_name") != "Chronos 1.0" or release.get("version") != "1.0" or
        release.get("phase") != 10 or release.get("release_ready") is not False or release.get("published") is not False or
        release.get("package_kind") != "local-review-package"):
        raise ValueError("Metadados devem identificar Chronos 1.0 como pacote local de revisão, sem liberação/publicação")
    policy = json.loads((root/"automation/n8n/security-status.json").read_text(encoding="utf-8"))
    status = json.loads((root/"docs/release/status.json").read_text(encoding="utf-8"))
    if policy.get("execution_allowed") is not False or status.get("production_ready") is not False or not status.get("pending_gates"):
        raise ValueError("Os bloqueios atuais devem permanecer explícitos no pacote")
    return release, status


def build_package(root, output, include_build=False):
    root, output = Path(root).resolve(), Path(output).absolute()
    if output.suffix.lower() != ".zip": raise ValueError("Use arquivo ZIP")
    if output.exists(): raise FileExistsError("Destino já existe; escolha outro nome")
    release, status = review_metadata(root)
    secrets = configured_secrets(root)
    sources = {}
    for path in selected_files(root, include_build):
        relative = path.relative_to(root).as_posix()
        if linked(path) or not path.resolve().is_relative_to(root): raise ValueError("Link de arquivo não permitido: " + relative)
        if path.stat().st_size > MAX_FILE: raise ValueError("Arquivo excede limite: " + relative)
        data = path.read_bytes()
        if any(value in data for value in secrets): raise ValueError("Segredo local encontrado em arquivo selecionado: " + relative)
        sources[relative] = data
    if len(sources) > MAX_FILES or sum(map(len, sources.values())) > MAX_BYTES: raise ValueError("Pacote excede limites")
    manifest = {"schema":"chronos-review-package-1.0", "product":"Chronos 1.0", "official_name":OFFICIAL,
        "phase":10,"package_kind":"local-review-package","release_ready":False,"published":False,
        "reference_date":release["date"],"frontend_build_included":include_build,"pending_gates":status["pending_gates"],
        "files":[{"path":name,"bytes":len(data),"sha256":sha(data)} for name,data in sorted(sources.items())]}
    output.parent.mkdir(parents=True,exist_ok=True)
    created = False
    try:
        with output.open("xb") as target:
            created = True
            with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
                for name,data in [*sorted(sources.items()), ("RELEASE-MANIFEST.json",canonical(manifest))]:
                    info=zipfile.ZipInfo(PREFIX+name,date_time=(1980,1,1,0,0,0))
                    info.compress_type=zipfile.ZIP_DEFLATED
                    info.external_attr=(stat.S_IFREG | 0o644)<<16
                    archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    except Exception:
        if created and output.is_file(): output.unlink()
        raise
    result=verify_package(output)
    return {**result,"archive_sha256":sha(output.read_bytes()),"archive_bytes":output.stat().st_size}


def safe_member(name):
    path=PurePosixPath(name)
    return name.startswith(PREFIX) and path.as_posix()==name and not path.is_absolute() and ".." not in path.parts and "\\" not in name and ":" not in name


def allowed_relative(name, include_build):
    if name in ROOT_FILES: return True
    parts=PurePosixPath(name).parts
    if len(parts)<2 or parts[0] not in SOURCE_DIRS or any(p.startswith(".") for p in parts): return False
    if parts[:2]==("frontend","dist"):
        return include_build and PurePosixPath(name).suffix.lower() in {".html",".js",".css",".svg",".woff2"}
    return (not any(p in SKIP_DIRS for p in parts) and PurePosixPath(name).suffix.lower() in EXTENSIONS and
        parts[-1].lower() not in {"credentials.json","secrets.json"})


def verify_package(path):
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist(); names=[e.filename for e in entries]
        if len(names) != len({name.casefold() for name in names}) or len(names)>MAX_FILES+1 or any(not safe_member(n) for n in names): raise ValueError("Caminhos inválidos ou duplicados no ZIP")
        if any(e.file_size>MAX_FILE or e.flag_bits & 1 or stat.S_IFMT(e.external_attr>>16) not in {0,stat.S_IFREG} for e in entries) or sum(e.file_size for e in entries)>MAX_BYTES+MAX_FILE:
            raise ValueError("Limites do ZIP excedidos")
        manifest=json.loads(archive.read(MANIFEST).decode("utf-8"))
        if (manifest.get("schema") != "chronos-review-package-1.0" or manifest.get("release_ready") is not False or manifest.get("published") is not False or
            manifest.get("official_name") != OFFICIAL or manifest.get("phase") != 10 or not manifest.get("pending_gates")):
            raise ValueError("Identidade ou bloqueios do manifesto inválidos")
        listed=[PREFIX+item["path"] for item in manifest["files"]]
        if any(not allowed_relative(item["path"],manifest.get("frontend_build_included") is True) for item in manifest["files"]):
            raise ValueError("Arquivo não permitido no pacote")
        if len(listed)!=len(set(listed)) or set(names)!={MANIFEST,*listed}: raise ValueError("Inventário divergente")
        for item in manifest["files"]:
            data=archive.read(PREFIX+item["path"])
            if len(data)!=item["bytes"] or sha(data)!=item["sha256"]: raise ValueError("Hash ou tamanho divergente: "+item["path"])
        if not {PREFIX+name for name in ROOT_FILES}.issubset(names): raise ValueError("Arquivos obrigatórios ausentes")
        release=json.loads(archive.read(PREFIX+"release.json").decode("utf-8"))
        status=json.loads(archive.read(PREFIX+"docs/release/status.json").decode("utf-8"))
        policy=json.loads(archive.read(PREFIX+"automation/n8n/security-status.json").decode("utf-8"))
        if (release.get("official_name")!=OFFICIAL or release.get("version")!="1.0" or release.get("phase")!=10 or
            release.get("release_ready") is not False or release.get("published") is not False or policy.get("execution_allowed") is not False or
            status.get("production_ready") is not False or status.get("pending_gates")!=manifest["pending_gates"]):
            raise ValueError("Metadados internos divergem dos bloqueios do manifesto")
    return {"product":"Chronos 1.0","verified":True,"file_count":len(listed),"manifest_sha256":sha(canonical(manifest)),
        "package_kind":"local-review-package","release_ready":False,"published":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    build=commands.add_parser("build"); build.add_argument("--output",type=Path,required=True); build.add_argument("--include-build",action="store_true")
    verify=commands.add_parser("verify"); verify.add_argument("archive",type=Path)
    args=parser.parse_args()
    if args.command=="verify": result=verify_package(args.archive)
    else:
        receipt=args.output.with_suffix(args.output.suffix+".receipt.json")
        if receipt.exists(): raise FileExistsError("Recibo já existe; escolha outro nome")
        result=build_package(ROOT,args.output,args.include_build)
        with receipt.open("xb") as target: target.write(canonical(result))
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__": main()
