from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
site = root.parent / 'portfolio'
datas = [(str(root / 'frontend/dist'), 'frontend/dist'),
    (str(root / 'data/synthetic/hospital_horizonte.json'), 'data/synthetic'),
    (str(root / 'desktop/chronos.ico'), 'desktop'),
    (str(root / 'desktop/solver-probe.json'), 'desktop'),
    (str(site / 'chronos-manual.html'), 'help'),
    (str(site / 'assets/chronos.css'), 'help/assets'),
    (str(site / 'img/chronos-mark.svg'), 'help/img')]
for source in (root / 'backend/alembic').rglob('*'):
    if source.is_file() and source.suffix in ('.py', '.mako') and '__pycache__' not in source.parts:
        datas.append((str(source), str(source.parent.relative_to(root))))
for package in ('ortools', 'fastapi', 'starlette', 'alembic', 'pydantic', 'uvicorn', 'argon2-cffi', 'tzdata'):
    datas += copy_metadata(package)
a = Analysis([str(root / 'desktop/launcher.py')], pathex=[str(root), str(root / 'backend')],
    binaries=collect_dynamic_libs('ortools'), datas=datas,
    hiddenimports=collect_submodules('app') + ['desktop.runtime', 'desktop.webapp', 'desktop.window', 'desktop.solver', 'desktop.selftest',
        'uvicorn.logging', 'uvicorn.loops.asyncio', 'uvicorn.protocols.http.h11_impl', 'uvicorn.lifespan.on',
        'sqlalchemy.dialects.sqlite', 'ortools.sat.python.cp_model', 'ortools.sat.python.cp_model_helper', 'tzdata'],
    excludes=['pytest', '_pytest', 'PyInstaller', 'psycopg', 'torch', 'matplotlib', 'IPython', 'notebook', 'scipy', 'jupyter', 'sphinx', 'edge_tts'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Chronos', debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    icon=str(root / 'desktop/chronos.ico'), version=str(root / 'desktop/version.txt'))
