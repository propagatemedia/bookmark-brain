import platform
import os

# Developer ID builds enable hardened runtime through PyInstaller.
identity = os.environ.get("BOOKMARK_SIGNING_IDENTITY")
if identity and not identity.startswith("Developer ID Application:"):
    raise ValueError("Use a Developer ID Application identity for direct distribution")

a = Analysis(['mac_launcher.py'], pathex=[], binaries=[], datas=[], hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Bookmark Brain', debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False, argv_emulation=False, target_arch='arm64', codesign_identity=identity, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Bookmark Brain')
app = BUNDLE(coll, name='Bookmark Brain.app', icon='assets/AppIcon.icns', bundle_identifier='media.propagate.bookmarkbrain', info_plist={'CFBundleShortVersionString':'1.10.3', 'CFBundleVersion':'1', 'LSUIElement': True, 'NSHighResolutionCapable': True, 'LSMinimumSystemVersion':platform.mac_ver()[0]})
