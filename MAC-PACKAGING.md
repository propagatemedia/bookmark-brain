# Terminal-free Mac packaging

The launcher runs a loopback HTTP server and a native menu-bar control. Bookmarks remain in the user's existing data folder. Packaging and testing must use temporary data, never a real library.

## Build requirements

Use a python.org universal2 Python 3.12 environment with `requirements-mac-build.txt`. Confirm `lipo -archs /path/to/python3` includes both `x86_64 arm64`. An arm64-only Homebrew Python cannot produce the Universal package.

`BB_TARGET_ARCH=arm64` (default) or `BB_TARGET_ARCH=universal2` controls the spec. Every collected Mach-O is audited for the required slices. The highest deployment target across those slices, with an 11.0 floor, becomes `LSMinimumSystemVersion` before the app bundle is signed. The result is printed and saved in `mac-binary-audit.json`; it never uses the build machine's OS version.

A binary deployment target is not proof of runtime compatibility. Do not advertise an older OS or Intel support until the candidate passes the appropriate launch tests. The currently published v1.10.3-beta.1 download remains Apple Silicon, tested on macOS 26.4.1. This branch does not change that download.

## Signing and verification

Follow [NOTARISATION.md](NOTARISATION.md) for Developer ID signing, notarisation and stapling. Build outside Google Drive so Finder attributes do not invalidate signatures. Never publish an unsigned intermediate bundle.

Run `python3 -m unittest discover -s tests -v` (24 existing product tests plus packaging tests). The bundled `--smoke-test` uses a temporary database. Universal candidates must pass this test natively and using `arch -x86_64`, then a manual launch on the oldest advertised macOS. Rosetta checks on a new Mac do not replace that older-OS test.
