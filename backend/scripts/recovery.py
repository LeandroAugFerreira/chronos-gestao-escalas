"""Chronos 1.0 — backup e restauração SQLite em diretório novo e isolado."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.recovery import backup_sqlite, restore_isolated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup")
    backup.add_argument("--source", required=True)
    backup.add_argument("--directory", required=True)
    restore = commands.add_parser("restore")
    restore.add_argument("--backup", required=True)
    restore.add_argument("--manifest", required=True)
    restore.add_argument("--directory", required=True)
    restore.add_argument("--confirm-isolated-restore", action="store_true", required=True)
    args = parser.parse_args()
    try:
        result = backup_sqlite(args.source, args.directory) if args.command == "backup" else restore_isolated(args.backup, args.manifest, args.directory)
    except Exception:
        # Never dump SQLite data, filenames from errors or credentials in a CLI traceback.
        parser.exit(1, "Recuperação não concluída. Confira integridade, hash, permissões e diretório novo fora do OneDrive.\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
