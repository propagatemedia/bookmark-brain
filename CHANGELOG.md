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
