"""Create one manifest for all final ZIPs in a staging folder, never upload."""
import argparse
import hashlib
from pathlib import Path
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('folder', type=Path)
a = p.parse_args()
files = sorted(a.folder.glob('*.zip'))
if not files or any(f.name == 'submission.zip' for f in files):
    p.error('Provide a staging folder containing final release ZIPs only')
lines = []
for f in files:
    with f.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    lines.append(f"{digest.hexdigest()}  {f.name}\n")
(a.folder / 'SHA256SUMS.txt').write_text(''.join(lines))
print(f'Checksums written for {len(files)} ZIPs. Verify Mac notarisation separately before publication.')
