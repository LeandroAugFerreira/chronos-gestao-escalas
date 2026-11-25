"""Auditable source distribution for 2.0; no installed dependencies or local data."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(output):
    release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    assert release["version"] == "2.0" and release["release_ready"] is False
    ignored = {"node_modules", ".venv", "__pycache__", ".pytest_cache", "dist", "releases", "artifacts", ".git"}
    names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    entries = []
    for name in sorted(set(filter(None, names))):
        path = ROOT / name
        if any(part in ignored for part in path.relative_to(ROOT).parts):
            raise ValueError("Local directory unexpectedly tracked: " + name)
        if (path.name.startswith(".env") and path.name != ".env.example") or path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".pem", ".key", ".log", ".exe"}:
            raise ValueError("Local data unexpectedly tracked: " + name)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Non-regular source: " + name)
        data = path.read_bytes()
        entries.append((name, data, hashlib.sha256(data).hexdigest()))
    manifest = {"product": "Chronos 2.0", "kind": "source-demonstration", "baseline_version": "1.0", "policy_version": release["policy_version"],
                "files": [{"path": name, "bytes": len(data), "sha256": digest} for name, data, digest in entries]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data, _ in entries:
            archive.writestr("Chronos-2.0/" + name, data)
        archive.writestr("Chronos-2.0/MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    return {"product": "Chronos 2.0", "file": output.name, "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "files": len(entries), "kind": "source-demonstration", "personal_accounts_included": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.output)
    args.output.with_name("Chronos-2.0-manifesto.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))
