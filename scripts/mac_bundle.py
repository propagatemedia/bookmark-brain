"""Fail-closed Mach-O architecture and deployment-target audit."""
from pathlib import Path
import re
import subprocess

MAGICS = {bytes.fromhex(x) for x in ('feedface', 'cefaedfe', 'feedfacf', 'cffaedfe', 'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca')}


def deployment_minimum(output):
    values = re.findall(r'^\s*minos\s+(\d+(?:\.\d+){1,2})\s*$', output, re.M)
    if not values:
        values = re.findall(r'^\s*version\s+(\d+(?:\.\d+){1,2})\s*$', output, re.M)
    if not values:
        raise ValueError('Mach-O has no recognised deployment target')
    return max(values, key=version_key)


def version_key(value):
    return tuple(int(v) for v in value.split('.')) + (0,) * (3 - len(value.split('.')))


def audit(folder, arch):
    required = {'arm64', 'x86_64'} if arch == 'universal2' else {'arm64'}
    records = []
    seen = set()
    for path in sorted(Path(folder).rglob('*')):
        if not path.is_file() or path.resolve() in seen:
            continue
        seen.add(path.resolve())
        with path.open('rb') as stream:
            if stream.read(4) not in MAGICS:
                continue
        slices = set(subprocess.check_output(['lipo', '-archs', str(path)], text=True).split())
        if not required <= slices:
            raise ValueError(f'{path}: missing {sorted(required - slices)}; found {sorted(slices)}')
        minima = {}
        for target in sorted(required):
            output = subprocess.check_output(['otool', '-arch', target, '-l', str(path)], text=True)
            # Only deployment commands: LC_ID_DYLIB also contains a version field.
            commands = re.split(r'Load command \d+\n', output)
            relevant = '\n'.join(c for c in commands if re.search(r'cmd LC_(BUILD_VERSION|VERSION_MIN_MACOSX)\b', c))
            minima[target] = deployment_minimum(relevant)
        records.append({'file': str(path.relative_to(folder)), 'architectures': sorted(slices), 'minimum': minima})
    if not records:
        raise ValueError('No Mach-O binaries found')
    minimum = max((v for record in records for v in record['minimum'].values()), key=version_key)
    minimum = max((minimum, '11.0'), key=version_key)
    return {'arch': arch, 'minimum_macos': minimum, 'binaries': records}
