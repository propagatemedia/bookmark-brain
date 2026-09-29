# v1.10.3-beta.1

- Expand all and Collapse all for the visible cards.
- Brain button enriches locally saved bookmarks on demand. Requests require confirmation; failures preserve existing content.
- Enrichment status survives backup and import. Older bookmarks have unknown status and offer enrichment without claiming they were never processed.

# v1.10.2-beta.1

- Bookmark notes and tags start collapsed. Expand or collapse each card; its state is retained during library updates in the current page.
- Includes the v1.10.1 provider rate-limit fix.

# v1.10.1-beta.1

- Rate-limited AI saves now keep the bookmark locally and show a notice.
- Serialise AI enrichment and pause requests for at least 60 seconds after HTTP 429, respecting numeric Retry-After up to one hour.
- Local-only fallback is not automatically enriched later.

# v1.10.0-beta.1

- Edit bookmark titles, notes, categories and tags locally.
- Import browser HTML and Bookmark Brain JSON without AI; merge missing links without overwriting existing records.
- Add daily pre-change backups, manual snapshots and missing-bookmark restore. Backups contain no API keys.
- Saving the same exact URL three times automatically favourites the single existing record. Bulk imports do not count; pre-upgrade bookmarks start at one.
- Add OpenRouter and provider model discovery with manual model entry retained.
- Add explicit connection tests using only a sample link, with a possible-charge confirmation.
- Modernise OpenAI requests to Responses API; preserve saved keys and model choices, remove stale model lists, and improve provider errors.
- Add upgrade instructions, migration tests and packaging verification.

Live OpenRouter catalogue verified. Paid AI generations were not tested with user credentials; model compatibility must be checked with Test connection. Apple Silicon/macOS 26.4.1+ local beta, not notarised.

# v1.9.1-beta.1

- Add a self-contained Apple Silicon Mac app with bundled Python and a native menu-bar launcher.
- Open the library and data folder, or quit cleanly, from the menu bar. No Terminal window required.
- Reuse the running packaged instance and select an available loopback port if 5055 is occupied.
- Preserve existing local data paths and never kill other processes.
- Remove the duplicate brain emoji from the browser title, keeping the favicon.
- Add launcher regression tests and packaged-runtime verification.

Tested on macOS 26.4.1, Apple Silicon. Ad-hoc signed only, not notarised. Public-download Gatekeeper approval and other Mac configurations remain unverified.

# v1.9.0-beta.1

- Default No AI mode saves bookmarks without provider credentials or external requests.
- Add a URL directly from the sidebar and export all bookmarks as JSON.
- Protect local APIs with a per-run token, Host and Origin checks; block cross-site browser requests.
- Escape HTML attributes, categories and settings embedded in scripts.
- Keep saved API keys out of HTTP responses, preserve blank keys on settings updates, add explicit key removal, and atomically write settings with owner-only permissions.
- Validate links, bound uploads and metadata, and hide provider error details.
- Stop processing drops twice and handle duplicate saves without duplicate rows.
- Serve concurrent requests so searches remain responsive during AI requests.
- Remove external font and favicon requests from the local app.
- Replace old paid-download and absolute offline/privacy claims with accurate setup and privacy notes.

Known limits: source beta requires Python 3.9+; no signed Mac installer; keys remain plaintext on disk; cloud sync/accounts/billing absent; live AI providers and Ollama not verified. Back up the local database with the app stopped. Do not sync a live SQLite file through cloud drives.
