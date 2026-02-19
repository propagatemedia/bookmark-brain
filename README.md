<div align="center">

<h1>🧠 Bookmark Brain</h1>

<p><strong>Finally, your saved links make sense.</strong></p>

<p>A local Mac app that reads your browser shortcut files, summarises every link with AI, and makes your entire bookmark library searchable in seconds. Works with any AI provider — or completely free and offline with Ollama.</p>

<p>
  <img src="https://img.shields.io/badge/version-1.7-purple?style=flat-square" />
  <img src="https://img.shields.io/badge/platform-macOS-black?style=flat-square" />
  <img src="https://img.shields.io/badge/python-3.8+-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/dependencies-none-brightgreen?style=flat-square" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" />
  <img src="https://img.shields.io/badge/price-$5%20once-orange?style=flat-square" />
</p>

<br/>

**[$5 → Get the Mac app on Gumroad](https://gumroad.com/l/bookmarkbrain)** &nbsp;·&nbsp; Self-build instructions below

<br/>

<img width="2208" height="955" alt="Bookmark Brain" src="https://github.com/user-attachments/assets/bd996bb3-eb2f-436f-82a5-d5054783c145" />


</div>

---

## The Origin

This started on a treadmill at 7am.

Mid-run, a thought: *"that tool I saved last week, the one for..."* — gone. Somewhere in the pile of browser favourites, desktop shortcuts, and a notes app full of context-free URLs.

Eleven words sent to an AI: **"I have so many shortcuts I can't find the ones I want or recall what they're all for."**

One conversation later, Bookmark Brain existed.

---

## What It Does

- **Drag** any `.webloc` (Safari) or `.url` (Chrome/Firefox) file — or drag a URL directly from your browser's address bar
- **AI reads** the URL and title, writes a 2–3 sentence plain-English summary of what the page is actually for
- **Smart categories** — YouTube, X / Twitter, LinkedIn, AI Image & Video and more are detected by domain before AI even runs
- **Star favourites** to pin them permanently to the top of your library
- **Search** across titles, summaries, tags, and domains instantly

---

## AI Providers

Switch between providers anytime in the Settings screen (⚙️ in the header). Your bookmarks never move.

| Provider | Models | Cost | Privacy |
|---|---|---|---|
| Anthropic | Claude Haiku, Sonnet, Opus | ~$0.01 / 500 bookmarks | URL + title sent to Anthropic |
| OpenAI | GPT-4o mini, GPT-4o | Similar | URL + title sent to OpenAI |
| Google Gemini | Gemini 2.0 Flash, 1.5 Pro | Very cheap | URL + title sent to Google |
| Groq | Llama 3.3, Mixtral | Free tier available | URL + title sent to Groq |
| **Ollama** | **Llama 3.2, Mistral, Phi3...** | **Free** | **Zero data leaves your Mac** |

**Ollama** runs AI models locally on your Mac. Nothing is ever sent anywhere. Install from [ollama.com](https://ollama.com), pull a model (`ollama pull llama3.2`), and Bookmark Brain handles the rest.

---

## Get It

### Option A — $5 Mac app (recommended)

**[Download on Gumroad →](https://gumroad.com/l/bookmarkbrain)**

1. Download and unzip `BookmarkBrain-v1.8.zip`
2. Drag `BookmarkBrain.app` to `/Applications`
3. Right-click → Open on first launch (one-time Gatekeeper bypass)
4. Enter your API key when prompted (or configure in Settings after launch)
5. Drag your first shortcut file in

> **Why $5?** The source code is completely free on GitHub. The $5 is for the packaged Mac app that just works — no terminal, no pip install, double-click and go.

> **Updating:** Just drag the new version to Applications → Replace. Your bookmarks and settings are untouched.

### Option B — Self-build (free)

No external packages needed. Uses only Python's standard library — no pip, no venv.

```bash
git clone https://github.com/yourusername/bookmark-brain.git
cd bookmark-brain
export ANTHROPIC_API_KEY="your-key-here"  # or configure another provider in-app
python3 app.py
```

Open [http://localhost:5055](http://localhost:5055) in your browser. Configure your preferred AI provider in Settings.

---

## Usage

**From Safari:** Drag the 🌐 globe icon from the address bar directly into the app.

**From Chrome / Firefox:** Drag the 🔒 lock icon — or drag a saved `.url` shortcut file.

**From Finder:** Select any number of `.webloc` or `.url` files and drag them all at once.

**Favourites:** Click the ☆ star on any card to pin it to the top of your library.

**Settings:** Click ⚙️ in the header to switch AI provider, change model, or update your API key.

---

## About localhost:5055

The app runs at `http://localhost:5055`. This is the loopback address — physically impossible to access from outside your machine.

- ✅ **No internet required** — works fully offline after first setup (especially with Ollama)
- ✅ **VPN-safe** — loopback addresses are never routed through VPNs
- ✅ **Works anywhere** — airplane mode, hotel wifi, corporate network
- ✅ **Completely private** — no one else can ever reach this address

Think of it like a file path — as reliable as opening a folder on your Mac.

---

## Privacy

| Data | Where it goes |
|---|---|
| Bookmark database | `~/Library/Application Support/BookmarkBrain/bookmarks.db` — your Mac only |
| Settings & API keys | `~/Library/Application Support/BookmarkBrain/settings.json` — your Mac only |
| URL + title (for AI summarisation) | Sent to whichever provider you choose in Settings |
| With Ollama | Nothing ever leaves your Mac |

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.8+ — stdlib only (http.server, urllib, sqlite3, plistlib) |
| AI | Anthropic / OpenAI / Gemini / Groq / Ollama — your choice |
| Database | SQLite |
| Frontend | Vanilla HTML / CSS / JS — no frameworks |
| Packaging | macOS .app bundle |

No Flask. No external packages. No pip install. Ever.

---

## Troubleshooting

**App won't open** → Right-click → Open on first launch to bypass Gatekeeper.

**"Python 3 not found"** → Install from [python.org](https://www.python.org/downloads/macos/) — free, takes 2 minutes. Relaunch after.

**Port already in use** → Quit any running instance (close the browser tab), then relaunch.

**Can't see my bookmarks after update** → Run in Terminal:
```bash
cp ~/BookmarkBrain/bookmarks.db ~/Library/Application\ Support/BookmarkBrain/bookmarks.db
```

**Lost your API key** → Open Settings (⚙️) and re-enter it. Or delete `~/Library/Application Support/BookmarkBrain/settings.json` to reset everything.

**Ollama not connecting** → Make sure Ollama is running (`ollama serve`) and you've pulled a model (`ollama pull llama3.2`).

---

## Google Drive Sync

Sync your bookmark database across multiple Macs:

1. Move `~/Library/Application Support/BookmarkBrain/bookmarks.db` to your Google Drive folder
2. Set the `BOOKMARK_DB` environment variable to the new path before launching

---

## Contributing

PRs welcome. Roadmap ideas:

- [ ] Browser extension for one-click import
- [ ] Export to Notion / Obsidian / CSV
- [ ] Bulk re-summarise with new provider
- [ ] Custom category definitions
- [ ] Windows / Linux support
- [ ] Scheduled auto-import from watched folder

---

## Licence

MIT — use it, fork it, build on it.

---

<div align="center">

**[$5 → Get the double-click Mac app](https://gumroad.com/l/bookmarkbrain)**

Built with frustration & Claude · by [Propagate Media](https://propagatemedia.com)

*Stop saving links. Start finding them.*

</div>
