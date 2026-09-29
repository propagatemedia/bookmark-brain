# Bookmark Brain for Windows

1. Download **Bookmark-Brain-Windows-x64.zip** from the [release](https://github.com/propagatemedia/bookmark-brain/releases/tag/v1.10.3-beta.1).
2. Right-click the ZIP and choose **Extract All**. Keep the whole extracted folder together.
3. Open the folder and double-click **Bookmark Brain.exe**. No Python or Terminal required.
4. Your browser opens the library. Minimise the small control window to keep the app running. Closing that window or clicking Quit stops it. Closing just the browser tab does not stop it.

Bookmarks, settings and backups live in `%LOCALAPPDATA%\BookmarkBrain`, separately from the program. To update, export a backup, quit the app, extract the new download to a new folder and run the new executable. Keep the data folder. Never run directly inside the ZIP or move only the executable out of its folder.

For another computer, Export on the old machine and import that JSON on the new one. API keys must be configured separately. There is no cloud sync.

This is an unsigned Windows x64 beta. It may trigger SmartScreen; only run a release you trust, and do not disable Windows security. The executable is built and smoke-tested on GitHub's Windows runner, including its control window, local saving, repeat-save favourites, backups, and single-instance handling. Consumer Windows 10/11 installation has not been manually validated. ARM-native and 32-bit builds are not provided.

The Windows asset is built from the Windows packaging commit on main and accompanies the v1.10.3 Mac release. Both include compact cards and the rate-limit fallback. See the Windows downloadable app Actions run for its exact source commit.
