# Upgrade to Bookmark Brain 1.10.1 beta

## The simple version

1. In your current Bookmark Brain window, click **Export**. Keep that JSON file somewhere safe.
2. Click the **brain in the Mac menu bar** and choose **Quit Bookmark Brain**. Closing its browser tab is not enough. If you still run the old Terminal version, stop that one with **Ctrl+C** too.
3. Download **Bookmark-Brain-Mac-Apple-Silicon.zip** from [this release](https://github.com/propagatemedia/bookmark-brain/releases/tag/v1.10.1-beta.1).
4. Unzip it in **Downloads**, outside Google Drive.
5. Drag **Bookmark Brain.app** into **Applications**. Choose **Replace** when asked.
6. Double-click the app in Applications. It opens the correct local address automatically. Check the header says **v1.10.1-beta.1**.

Your bookmarks and settings live separately in `~/Library/Application Support/BookmarkBrain`. Replacing the app keeps them. Do not delete that data folder. If you use a custom BOOKMARK_DB or BOOKMARK_SUPPORT path, continue using that same configuration; the normal app uses the default path above.

If your old browser tab still shows the old version, close it and use **Open Bookmark Brain** in the brain menu. Do not assume port 5055: another running copy can make the app choose another port.

## New features

- **Edit:** click Edit on a bookmark to change its title, notes, category and tags. No AI needed.
- **Browser import:** in Chrome/Safari, export bookmarks as an HTML file. In Bookmark Brain choose **Import / backups**, choose the file, then **Import selected file**. JSON exports work too. Existing links remain unchanged, and imports never call AI.
- **Backups:** the app takes a private local JSON snapshot before the first bookmark change each UTC day and before an import or restore. Choose **Back up now** for another snapshot. Find them in the data folder's `backups` directory. They are retained until you manage them yourself and do not replace a backup on another device.
- **Restore:** select a backup, then **Restore missing bookmarks**. This adds missing links without undoing edits or replacing existing links. You can also import an older exported JSON file. It is not a full rollback.
- **Repeat-save favourites:** saving or dropping the exact same URL for the third time automatically stars the existing bookmark. It stays a single record. Bulk HTML/JSON import does not increase this counter. Old bookmarks start with a count of one on upgrade, because earlier versions did not record their historical drops.

## Set up OpenRouter or another AI provider

1. Open **Settings** using the cog.
2. Choose **OpenRouter**, **OpenAI**, **Anthropic**, **Gemini**, **Groq** or **Ollama**. Groq and Grok are different services.
3. Paste that provider's API key. OpenRouter needs an OpenRouter key; OpenAI needs an OpenAI API key. Ollama runs locally and needs no key.
4. Click **Load models**, then start typing in **Model** and pick one from the suggestions. Manual model IDs also work. For Ollama, install and download a model first.
5. Click **Test connection** and confirm the small possible provider charge. It sends only a sample example.com link and uses at most 1,600 output tokens, not your bookmarks. A successful test checks both access and the JSON response format.
6. Click **Save Settings**. Existing keys are preserved when the key field is blank; use **Remove saved key** to clear one.

Existing model selections are preserved on upgrade, even if the provider has retired them. Use Load models and test a replacement. Provider catalogues do not guarantee model access, pricing or compatibility. No automatic switch to a more expensive model is made.

With AI enabled, new links send their URL and title to your selected provider. Descriptions are inferred suggestions, not verified page contents. Editing and HTML/JSON importing are always local. Choose **No AI** to save without generation requests.

## Compatibility

Apple Silicon, macOS 26.4.1 or newer; tested on macOS 26.4.1. Intel and older macOS builds are not included. This beta is ad-hoc signed, not Apple-notarised. macOS may block a downloaded copy. If blocked, use Apple's per-app approval flow only if you trust this GitHub release; never disable Gatekeeper globally. No cloud accounts, billing or automatic app updates are enabled.

## Provider rate limits

If a provider returns a rate-limit or quota error, the bookmark is saved locally without AI and the app shows a notice. Further enrichment pauses for at least 60 seconds (longer when the provider requests it). These bookmarks are not automatically enriched later. If limits continue, check your provider quota or balance, or choose No AI.
