# Terminal-free local Mac build

`mac_launcher.py` runs the existing HTTP app in a background thread and offers a native menu bar with Open, Open data folder and Quit. It keeps the existing data paths. A file lock prevents duplicate packaged instances; port conflicts fall back to a free loopback port without killing anything. Python and Cocoa dependencies are bundled by PyInstaller.

## Build

Create `.venv-mac` using Python 3.12, then install `requirements-mac-build.txt` into it. Run:

```sh
.venv-mac/bin/pyinstaller --noconfirm BookmarkBrain.spec
```

The spec targets arm64 and conservatively sets the minimum OS to the build Mac's macOS version. This local build was tested on macOS 26.4.1. It is not an Intel or older-macOS release.

Google Drive can add FinderInfo attributes to bundle directories and interfere with signature validation. Copy the generated bundle to a local temporary directory using `ditto --norsrc --noextattr`, run `codesign --verify --deep --strict` there, then ZIP that clean copy. Distribute the ZIP, not a live app bundle in Google Drive.

## Verify

- `python3 -m unittest discover -s tests -v`: 23 tests, including launcher exclusivity and port fallback.
- Run the bundled `Contents/MacOS/Bookmark Brain --smoke-test`: uses a temporary database to verify bundled SQLite, HTTP saving and title rendering.
- Launch through macOS `open` with `BOOKMARK_SUPPORT` pointing at a dedicated `/tmp/` path, `BOOKMARK_NO_BROWSER=1` and `BOOKMARK_TEST_EXIT_SECONDS=8` for a timed menu-app lifecycle check. Confirm that the local HTTP endpoint starts and stops and the lock is released.

The local bundle is ad-hoc signed. Developer ID signing, notarisation, public release and website download replacement are not part of this local packaging task.
