"""Package the user-facing PDF and dependency-free Raspberry Pi setup scripts."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent.parent
target = root / 'downloads/Exhibition-Setup-Kit.zip'
target.parent.mkdir(parents=True, exist_ok=True)
manual = root / 'docs/Two-Screen-Exhibition-Manual.pdf'
if not manual.is_file():
    raise SystemExit('Build docs/Two-Screen-Exhibition-Manual.pdf first.')
files = sorted(p for p in (root / 'exhibit-kit').iterdir() if p.is_file() and p.suffix in ('.py', '.sh', '.txt'))
with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    archive.write(manual, manual.name)
    for file in files:
        archive.write(file, 'exhibit-kit/' + file.name)
print(target)
