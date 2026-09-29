# Bookmark Brain desktop beta

A local bookmark library with search, categories, favourites, shortcut import and JSON export. This is the original desktop product, maintained separately from the [web demo](https://www.bookmarkbrain.co/demo).

[Simple upgrade and feature guide](UPGRADE.md)

## Mac app: no Terminal or Python installation needed

[Download the Apple Silicon Mac app](https://github.com/propagatemedia/bookmark-brain/releases/download/v1.10.2-beta.1/Bookmark-Brain-Mac-Apple-Silicon.zip).

1. Extract the ZIP into Downloads, outside Google Drive.
2. Drag **Bookmark Brain.app** into Applications and double-click it.
3. The browser opens your library. Use the brain icon in the menu bar to reopen it or quit.

Python is included, and existing bookmarks stay in the same local data folder. Closing the browser tab does not quit the app. If the old Terminal version is running, the packaged app chooses another available port without stopping other processes.

**Compatibility:** this build targets Apple Silicon and macOS 26.4.1 or newer, and was tested on macOS 26.4.1. Intel Macs and older macOS versions are not supported by this build. It is an ad-hoc signed beta, not Developer ID signed or Apple-notarised; macOS may block downloaded copies. Do not disable Gatekeeper globally. The source version below remains available.

[Release notes and checksum](https://github.com/propagatemedia/bookmark-brain/releases/tag/v1.10.2-beta.1) · [Build instructions](MAC-PACKAGING.md)

## Windows app: no Terminal or Python installation needed

[Download the Windows x64 app](https://github.com/propagatemedia/bookmark-brain/releases/download/v1.10.2-beta.1/Bookmark-Brain-Windows-x64.zip).

Extract All, open the extracted folder and double-click **Bookmark Brain.exe**. Keep the whole folder together. Minimise the control window to keep running; close it to quit. Bookmarks are stored in `%LOCALAPPDATA%\BookmarkBrain`, separately from the download.

This unsigned beta is built and smoke-tested on a Windows runner. Manual Windows 10/11 installation has not been verified. [Windows setup and upgrade guide](WINDOWS.md).

## Download and run the source version

[Download v1.10.2-beta.1](https://github.com/propagatemedia/bookmark-brain/releases/tag/v1.10.2-beta.1).

This is a **free source beta requiring Python 3.9 or newer**, not a signed or notarised Mac installer. No Python packages or paid AI key are required for normal bookmark storage. The ZIP contains source code and a Mac Terminal launcher; it does not bundle Python.

1. Install Python from [python.org](https://www.python.org/downloads/macos/) if needed.
2. Download and unzip `BookmarkBrain-v1.10.2-beta.1.zip` from the release page.
3. Open Terminal in the extracted folder and run `python3 app.py`. On a Mac, `bash Start-Bookmark-Brain.command` does the same thing.
4. Open **http://127.0.0.1:5055** in your browser.
5. Paste a URL into the sidebar or drop a `.webloc` or `.url` file. Bookmarks save immediately with the default **No AI** setting.

Keep Terminal running. Press Ctrl+C to stop the server. Closing the browser tab does not stop it. If port 5055 is occupied, use `BOOKMARK_PORT=5056 python3 app.py` and open the matching URL. The launcher never kills other processes.

Alternatively:

```sh
git clone https://github.com/propagatemedia/bookmark-brain.git
cd bookmark-brain
python3 app.py
```

## Data and privacy

- Bookmarks persist in `~/Library/Application Support/BookmarkBrain/bookmarks.db`.
- Settings are in `settings.json` in the same directory. Saved API keys are plaintext, restricted to the current filesystem user with mode 0600. They are not stored in macOS Keychain. Do not share this directory.
- The server binds to `127.0.0.1` and rejects unrecognised hosts, cross-site requests and API requests without its per-run token. This does not protect against malicious software already running under your user account.
- With **No AI**, the app does not make external requests. Fonts and favicons do not contact third parties. Saving, searching and browsing your library work offline; opening websites requires their usual connection.
- Optional cloud AI sends the URL and title to the provider you select, using your own key. Provider charges and model availability vary. No page scraping happens: summaries are suggestions inferred from the URL and title, not verified descriptions of page contents.
- Ollama requires a separately installed local service and model. Its configured endpoint must be a loopback address. Its live integration and the cloud AI providers have not been verified in this beta audit.

## Backups and export

Use **Export** to download all bookmarks as JSON. The web demo can import this JSON, subject to its demo limits. The desktop app imports shortcut files, browser HTML and Bookmark Brain JSON. Use Import / backups to create a snapshot or restore missing links. Restore merges missing bookmarks; it does not roll back edits. Automatic local snapshots run before the first change each UTC day and before imports. Keep a copy of the SQLite database while the app is stopped to restore a complete desktop library. Do not put a live SQLite database in Google Drive or another file-sync folder: concurrent syncing can corrupt it. Cloud sync is not implemented in this desktop app.

`BOOKMARK_SUPPORT` and `BOOKMARK_DB` can override local data paths. Use a dedicated local directory. Do not expose this server publicly or use it as a multi-user service.

## Verification and known limits

```sh
python3 -m unittest discover -s tests -v
```

Automated tests cover persistence, search, favourites, duplicate detection, shortcut import, request protections, secret masking, settings permissions, invalid URLs and AI failures. Browser smoke tests cover saving and searching. This is a beta, not a claim of a complete security audit or a production SaaS launch.

The old $5 Gumroad download is no longer promoted: no packaged download was available in GitHub Releases during this audit. Accounts, subscriptions and cloud sync belong to the separate web project and are not connected yet.

MIT licence. Built by Propagate Media.
