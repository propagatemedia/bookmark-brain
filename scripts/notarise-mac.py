"""Prepare, submit and staple a Developer ID build. Never publishes automatically."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import plistlib
from mac_bundle import audit

ROOT = Path(__file__).resolve().parents[1]


def run(*args, capture=False, env=None):
    return subprocess.run([str(a) for a in args], cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None, env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'submit', 'finalise', 'release'])
    parser.add_argument('--workspace', type=Path, help='The temporary folder printed by prepare')
    parser.add_argument('--identity', help='Full Developer ID Application certificate name')
    parser.add_argument('--profile', default='bookmark-brain-notary', help='notarytool Keychain profile name')
    parser.add_argument('--arch', choices=['arm64', 'universal2'], default='arm64')
    parser.add_argument('--python', default=sys.executable, help='Python environment containing PyInstaller')
    args = parser.parse_args()
    if args.stage in ('prepare', 'release'):
        if not args.identity or not args.identity.startswith('Developer ID Application:'):
            parser.error('prepare requires --identity with a Developer ID Application certificate')
        identities = run('security', 'find-identity', '-v', '-p', 'codesigning', capture=True).stdout
        if '"' + args.identity + '"' not in identities:
            parser.error('The requested valid signing identity is not available in this Mac keychain')
        work = Path(tempfile.mkdtemp(prefix='bookmark-brain-notarise-'))
        env = dict(os.environ, BOOKMARK_SIGNING_IDENTITY=args.identity, BB_TARGET_ARCH=args.arch)
        run(args.python, '-m', 'PyInstaller', '--noconfirm', '--distpath', work / 'dist',
            '--workpath', work / 'build', 'BookmarkBrain.spec', env=env)
        bundle = work / 'dist/Bookmark Brain.app'
        report = audit(bundle, args.arch)
        (work / 'mac-binary-audit.json').write_text(json.dumps(report, indent=2))
        with (bundle / 'Contents/Info.plist').open('rb') as stream:
            if plistlib.load(stream)['LSMinimumSystemVersion'] != report['minimum_macos']:
                raise SystemExit('Info.plist minimum does not match the binary audit')
        print('Computed macOS minimum:', report['minimum_macos'])
        run('codesign', '--verify', '--deep', '--strict', bundle)
        run(bundle / 'Contents/MacOS/Bookmark Brain', '--smoke-test')
        if args.arch == 'universal2':
            run('arch', '-x86_64', bundle / 'Contents/MacOS/Bookmark Brain', '--smoke-test')
        run('ditto', '-c', '-k', '--keepParent', '--norsrc', '--noextattr', bundle, work / 'submission.zip')
        print('Prepared workspace:', work)
        if args.stage == 'prepare':
            return
        args.workspace = work
    if not args.workspace:
        parser.error('provide --workspace from prepare')
    work = args.workspace.resolve()
    bundle = work / 'dist/Bookmark Brain.app'
    if not bundle.is_dir() or not (work / 'submission.zip').is_file():
        parser.error('workspace is missing its prepared bundle or submission ZIP')
    if args.stage in ('submit', 'release'):
        if (work / 'submission.json').exists():
            parser.error('A submission already exists; inspect its status rather than submitting twice')
        command = ['xcrun', 'notarytool', 'submit', work / 'submission.zip', '--keychain-profile',
                     args.profile, '--output-format', 'json', *(['--wait'] if args.stage == 'release' else [])]
        response = subprocess.run([str(v) for v in command], text=True, stdout=subprocess.PIPE)
        result = json.loads(response.stdout)
        if not result.get('id'):
            raise SystemExit('Apple did not return a submission ID; inspect the response before retrying')
        (work / 'submission.json').write_text(json.dumps(result, indent=2))
        print('Submitted:', result['id'])
        print('Run finalise after Apple completes its review. No release has been published.')
        if args.stage == 'submit':
            return
    submission = json.loads((work / 'submission.json').read_text())['id']
    status = json.loads(run('xcrun', 'notarytool', 'info', submission, '--keychain-profile', args.profile,
                            '--output-format', 'json', capture=True).stdout)
    (work / 'status.json').write_text(json.dumps(status, indent=2))
    if status.get('status') != 'Accepted':
        print(f'xcrun notarytool log {submission} --keychain-profile {args.profile}')
        raise SystemExit('Not ready to distribute. Apple status: ' + str(status.get('status')))
    run('xcrun', 'notarytool', 'log', submission, '--keychain-profile', args.profile, work / 'notary-log.json')
    run('xcrun', 'stapler', 'staple', bundle)
    run('xcrun', 'stapler', 'validate', bundle)
    run('codesign', '--verify', '--deep', '--strict', bundle)
    run('spctl', '--assess', '--type', 'execute', '--verbose=2', bundle)
    verification = []
    for command in [('codesign', '-dv', '--verbose=4', bundle), ('spctl', '-a', '-vv', '-t', 'exec', bundle)]:
        result = subprocess.run([str(v) for v in command], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        verification.append(result.stdout)
        print(result.stdout)
    output = '\n'.join(verification)
    (work / 'verification.txt').write_text(output)
    for required in ('Authority=Developer ID Application:', 'Timestamp=', 'runtime', 'source=Notarized Developer ID'):
        if required not in output:
            raise SystemExit('Missing verification evidence: ' + required)
    report = json.loads((work / 'mac-binary-audit.json').read_text())
    audit(bundle, report['arch'])
    label = 'Universal' if report['arch'] == 'universal2' else 'Apple-Silicon'
    archive = work / f'Bookmark-Brain-Mac-{label}.zip'
    run('ditto', '-c', '-k', '--keepParent', '--norsrc', '--noextattr', bundle, archive)
    check = Path(tempfile.mkdtemp(prefix='bookmark-brain-notarised-check-'))
    run('ditto', '-x', '-k', archive, check)
    extracted = check / 'Bookmark Brain.app'
    run('xcrun', 'stapler', 'validate', extracted)
    run(extracted / 'Contents/MacOS/Bookmark Brain', '--smoke-test')
    if report['arch'] == 'universal2':
        run('arch', '-x86_64', extracted / 'Contents/MacOS/Bookmark Brain', '--smoke-test')
    (work / 'SHA256SUMS.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    print('Verified archive:', archive)
    print('Review notary-log.json and test a downloaded copy before publishing.')


if __name__ == '__main__':
    main()
