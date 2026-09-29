"""Build an explicit, credential-free source ZIP and SHA-256 manifest."""
from pathlib import Path
import hashlib
import zipfile

root = Path(__file__).resolve().parent
version = '1.9.0-beta.1'
files = ['app.py', 'README.md', 'LICENSE', 'CHANGELOG.md', 'Start-Bookmark-Brain.command', 'build-release.py', 'tests/test_app.py']
output = root / 'dist'
output.mkdir(exist_ok=True)
archive = output / f'BookmarkBrain-v{version}.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for name in files:
        z.write(root / name, f'BookmarkBrain-v{version}/{name}')
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(output / 'SHA256SUMS.txt').write_text(f'{checksum}  {archive.name}\n')
print(f'{archive.name}: {checksum}')
