"""Update version references for a future release; never builds or publishes."""
import argparse
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('version')
a = p.parse_args()
if not re.fullmatch(r'\d+\.\d+\.\d+-beta\.\d+', a.version):
    p.error('Expected X.Y.Z-beta.N')
old = (ROOT / 'VERSION').read_text().strip()
for name in ['app.py', 'build-release.py', 'README.md', 'UPGRADE.md', 'WINDOWS.md']:
    path = ROOT / name
    path.write_text(path.read_text().replace(old, a.version))
path = ROOT / 'BookmarkBrain.spec'
s = path.read_text().replace("'CFBundleShortVersionString':'" + old.split('-')[0] + "'", "'CFBundleShortVersionString':'" + a.version.split('-')[0] + "'")
s = s.replace("'CFBundleVersion':'" + old.rsplit('.',1)[1] + "'", "'CFBundleVersion':'" + a.version.rsplit('.',1)[1] + "'")
path.write_text(s)
(ROOT / 'VERSION').write_text(a.version + '\n')
print('Updated version references. Review future asset links before committing or releasing.')
