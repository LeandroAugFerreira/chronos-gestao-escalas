"""Chronos 1.0: reaproveita o perfil PostgreSQL de teste do .env, sem mostrar credenciais."""

import os
from pathlib import Path
import sys

from dotenv import dotenv_values
import pytest

root = Path(__file__).resolve().parents[2]
value = dotenv_values(root / ".env").get("CHRONOS_TEST_POSTGRES_URL")
if value and "CHRONOS_TEST_POSTGRES_URL" not in os.environ:
    os.environ["CHRONOS_TEST_POSTGRES_URL"] = value
os.chdir(root / "backend")
raise SystemExit(pytest.main(sys.argv[1:] or ["-q"]))
