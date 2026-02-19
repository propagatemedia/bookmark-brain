#!/usr/bin/env python3
"""
Bookmark Brain v1.8 — Multi-provider AI support
Providers: Anthropic, OpenAI, Google Gemini, Groq, Ollama
Zero external dependencies — Python stdlib only.
"""

import os, json, sqlite3, plistlib, re, urllib.request, urllib.error, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote
from pathlib import Path

PORT = 5055
SUPPORT_DIR = os.environ.get("BOOKMARK_SUPPORT",
    str(Path.home() / "Library" / "Application Support" / "BookmarkBrain"))
DB_PATH = os.environ.get("BOOKMARK_DB", str(Path(SUPPORT_DIR) / "bookmarks.db"))
SETTINGS_PATH = str(Path(SUPPORT_DIR) / "settings.json")
_db_lock = threading.Lock()

# ── Default settings ─────────────────────────────────────
DEFAULT_SETTINGS = {
    "provider": "anthropic",
    "providers": {
        "anthropic": {"api_key": os.environ.get("ANTHROPIC_API_KEY",""), "model": "claude-haiku-4-5-20251001"},
        "openai":    {"api_key": "", "model": "gpt-4o-mini"},
        "gemini":    {"api_key": "", "model": "gemini-2.0-flash"},
        "groq":      {"api_key": "", "model": "llama-3.1-8b-instant"},
        "ollama":    {"api_key": "", "model": "llama3.2", "base_url": "http://localhost:11434"},
    }
}

PROVIDER_MODELS = {
    "anthropic": ["claude-haiku-4-5-20251001", "claude-sonnet-4-5-20251001", "claude-opus-4-5-20251001"],
    "openai":    ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
    "gemini":    ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    "groq":      ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
    "ollama":    ["llama3.2", "llama3.1", "mistral", "phi3", "gemma2"],
}

PROVIDER_LABELS = {
    "anthropic": "Anthropic (Claude)",
    "openai":    "OpenAI (GPT)",
    "gemini":    "Google Gemini",
    "groq":      "Groq",
    "ollama":    "Ollama (Local / Free)",
}

# ── Settings I/O ─────────────────────────────────────────
def load_settings():
    try:
        with open(SETTINGS_PATH) as f:
            saved = json.load(f)
        # Deep merge with defaults so new keys always exist
        s = json.loads(json.dumps(DEFAULT_SETTINGS))
        s["provider"] = saved.get("provider", s["provider"])
        for p in s["providers"]:
            if p in saved.get("providers", {}):
                s["providers"][p].update(saved["providers"][p])
        return s
    except Exception:
        return json.loads(json.dumps(DEFAULT_SETTINGS))

def save_settings(s):
    os.makedirs(SUPPORT_DIR, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(s, f, indent=2)

# ── Database ─────────────────────────────────────────────
def get_db():
    os.makedirs(SUPPORT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE NOT NULL,
        title TEXT, summary TEXT, category TEXT, tags TEXT,
        domain TEXT, favourite INTEGER DEFAULT 0,
        added_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.commit()
    try:
        conn.execute("ALTER TABLE bookmarks ADD COLUMN favourite INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    return conn

# ── Domain → forced category ─────────────────────────────
DOMAIN_CATS = {
    "youtube.com":"YouTube","youtu.be":"YouTube",
    "x.com":"X / Twitter","twitter.com":"X / Twitter",
    "instagram.com":"Instagram","linkedin.com":"LinkedIn",
    "facebook.com":"Facebook","reddit.com":"Reddit",
    "github.com":"Development","gitlab.com":"Development",
    "midjourney.com":"AI Image & Video","runway.com":"AI Image & Video",
    "pika.art":"AI Image & Video","kling.ai":"AI Image & Video",
    "ideogram.ai":"AI Image & Video","leonardo.ai":"AI Image & Video",
    "sora.com":"AI Image & Video","invideo.io":"AI Image & Video",
    "openai.com":"AI Tools","anthropic.com":"AI Tools",
    "claude.ai":"AI Tools","perplexity.ai":"AI Tools",
    "gemini.google.com":"AI Tools","copilot.microsoft.com":"AI Tools",
}

def forced_category(domain):
    d = domain.lower().replace("www.","")
    for k, v in DOMAIN_CATS.items():
        if d == k or d.endswith("."+k): return v
    return None

# ── URL extraction from shortcut files ───────────────────
def extract_url(filename, content_bytes):
    ext = Path(filename).suffix.lower()
    if ext == ".webloc":
        try: return plistlib.loads(content_bytes).get("URL","")
        except Exception:
            m = re.search(r'<string>(https?://[^<]+)</string>', content_bytes.decode("utf-8",errors="ignore"))
            return m.group(1) if m else ""
    elif ext in (".url",".desktop"):
        m = re.search(r'URL=(.+)', content_bytes.decode("utf-8",errors="ignore"), re.IGNORECASE)
        return m.group(1).strip() if m else ""
    t = content_bytes.decode("utf-8",errors="ignore").strip()
    return t if t.startswith("http") else ""

# ── AI provider calls ─────────────────────────────────────
PROMPT_TEMPLATE = """Analyze this web bookmark and return ONLY valid JSON (no markdown, no explanation).

URL: {url}
Domain: {domain}
Title: {title}

Return exactly:
{{
  "title": "clean readable title",
  "summary": "2-3 sentence summary of what this page is about",
  "category": "one of: Tools, Reference, News, Social, Shopping, Development, Design, Marketing, Education, Finance, Entertainment, Business, Health, Travel, Sports, AI Tools, AI Image & Video, YouTube, X / Twitter, Instagram, LinkedIn, Reddit, Other",
  "tags": ["tag1", "tag2", "tag3"]
}}"""

def http_post(url, headers, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={**headers, "content-type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def parse_ai_json(text):
    raw = re.sub(r'^```(?:json)?\s*|\s*```$','', text.strip())
    return json.loads(raw)

def call_anthropic(prompt, cfg):
    result = http_post("https://api.anthropic.com/v1/messages",
        {"x-api-key": cfg["api_key"], "anthropic-version": "2023-06-01"},
        {"model": cfg["model"], "max_tokens": 400,
         "messages": [{"role":"user","content":prompt}]})
    return parse_ai_json(result["content"][0]["text"])

def call_openai(prompt, cfg):
    result = http_post("https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {cfg['api_key']}"},
        {"model": cfg["model"], "max_tokens": 400, "temperature": 0.3,
         "messages": [{"role":"user","content":prompt}]})
    return parse_ai_json(result["choices"][0]["message"]["content"])

def call_gemini(prompt, cfg):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{cfg['model']}:generateContent?key={cfg['api_key']}"
    req = urllib.request.Request(url,
        data=json.dumps({"contents":[{"parts":[{"text":prompt}]}],
                         "generationConfig":{"maxOutputTokens":400,"temperature":0.3}}).encode(),
        headers={"content-type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
    return parse_ai_json(result["candidates"][0]["content"]["parts"][0]["text"])

def call_groq(prompt, cfg):
    result = http_post("https://api.groq.com/openai/v1/chat/completions",
        {"Authorization": f"Bearer {cfg['api_key']}"},
        {"model": cfg["model"], "max_tokens": 400, "temperature": 0.3,
         "messages": [{"role":"user","content":prompt}]})
    return parse_ai_json(result["choices"][0]["message"]["content"])

def call_ollama(prompt, cfg):
    base = cfg.get("base_url","http://localhost:11434").rstrip("/")
    result = http_post(f"{base}/api/chat", {},
        {"model": cfg["model"], "stream": False,
         "messages": [{"role":"user","content":prompt}]})
    return parse_ai_json(result["message"]["content"])

CALLERS = {
    "anthropic": call_anthropic,
    "openai":    call_openai,
    "gemini":    call_gemini,
    "groq":      call_groq,
    "ollama":    call_ollama,
}

def analyze_bookmark(url, title=""):
    domain = urlparse(url).netloc.replace("www.","")
    fcat = forced_category(domain)
    prompt = PROMPT_TEMPLATE.format(url=url, domain=domain, title=title or "(not available)")
    settings = load_settings()
    provider = settings["provider"]
    cfg = settings["providers"].get(provider, {})
    caller = CALLERS.get(provider)
    if not caller:
        raise ValueError(f"Unknown provider: {provider}")
    data = caller(prompt, cfg)
    if fcat:
        data["category"] = fcat
    return data

# ── Multipart parser ──────────────────────────────────────
def parse_multipart(rfile, content_type, content_length):
    boundary = None
    for p in content_type.split(";"):
        p = p.strip()
        if p.startswith("boundary="): boundary = p[9:].strip('"').encode()
    if not boundary: return []
    body = rfile.read(content_length); files = []
    for part in body.split(b"--" + boundary)[1:]:
        if part.startswith(b"--"): break
        if b"\r\n\r\n" not in part: continue
        hdrs, data = part.split(b"\r\n\r\n", 1)
        data = data.rstrip(b"\r\n")
        m = re.search(r'filename="([^"]+)"', hdrs.decode("utf-8",errors="ignore"))
        if m: files.append((m.group(1), data))
    return files

# ── HTML ──────────────────────────────────────────────────
def build_html(settings):
    provider = settings["provider"]
    providers_json = json.dumps(settings["providers"])
    provider_models_json = json.dumps(PROVIDER_MODELS)
    provider_labels_json = json.dumps(PROVIDER_LABELS)
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🧠 Bookmark Brain v1.8</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🧠</text></svg>">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#08060f;--bg2:#0d0b18;--surface:#12101f;--surface2:#1a1729;
  --border:#2a2640;--purple:#8b5cf6;--purple2:#a78bfa;--pink:#f472b6;
  --accent:#e8527a;--text:#f0eeff;--muted:#8b87aa;--gold:#fbbf24;--green:#4ade80;
}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{background:var(--bg2);border-bottom:1px solid var(--border);padding:0 18px;height:50px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;gap:12px}
.logo{font-weight:700;font-size:15px;display:flex;align-items:center;gap:7px;white-space:nowrap}
.ver{font-family:'DM Mono',monospace;font-size:10px;color:var(--muted)}
.header-mid{flex:1;display:flex;align-items:center;justify-content:center}
.provider-pill{display:flex;align-items:center;gap:6px;background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:4px 10px 4px 8px;font-size:11px;color:var(--muted);cursor:pointer;transition:all .2s}
.provider-pill:hover{border-color:var(--purple);color:var(--text)}
.provider-dot{width:7px;height:7px;border-radius:50%;background:var(--green)}
.header-right{display:flex;align-items:center;gap:12px}
.stats{display:flex;gap:14px}
.stat{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted)}
.stat b{color:var(--purple2)}
.settings-btn{background:none;border:none;color:var(--muted);cursor:pointer;font-size:17px;padding:4px;border-radius:6px;transition:all .2s;line-height:1}
.settings-btn:hover{color:var(--text);background:var(--surface)}
.search-bar{background:var(--bg2);border-bottom:1px solid var(--border);padding:8px 16px;flex-shrink:0}
.search-input{width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 13px;color:var(--text);font-size:13px;outline:none;transition:border-color .2s}
.search-input:focus{border-color:var(--purple)}
.search-input::placeholder{color:var(--muted)}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:188px;background:var(--bg2);border-right:1px solid var(--border);overflow-y:auto;flex-shrink:0;display:flex;flex-direction:column}
.dropzone{margin:10px;border:1.5px dashed var(--border);border-radius:10px;padding:14px 10px;text-align:center;cursor:pointer;transition:all .2s;flex-shrink:0}
.dropzone.over{border-color:var(--purple);background:rgba(139,92,246,.06)}
.dz-icon{font-size:18px;margin-bottom:4px}
.dz-text{font-size:11px;color:var(--muted);line-height:1.5}
.dz-text strong{color:var(--text);display:block;font-size:12px;margin-bottom:1px}
.sidebar-label{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);padding:9px 12px 4px}
.cat-btn{width:100%;text-align:left;background:none;border:none;padding:5px 12px;color:var(--muted);font-size:12px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;transition:all .15s}
.cat-btn:hover{background:var(--surface);color:var(--text)}
.cat-btn.active{background:rgba(139,92,246,.12);color:var(--purple2);border-right:2px solid var(--purple)}
.fav-btn.active{background:rgba(251,191,36,.08)!important;color:var(--gold)!important;border-right-color:var(--gold)!important}
.cat-count{font-family:'DM Mono',monospace;font-size:10px;flex-shrink:0;margin-left:3px}
.content{flex:1;overflow-y:auto;padding:13px 16px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:9px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:13px;transition:all .2s;position:relative}
.card:hover{border-color:rgba(139,92,246,.3);background:var(--surface2)}
.card.fav{border-color:rgba(251,191,36,.22)}
.card-actions{position:absolute;top:9px;right:9px;display:flex;gap:1px;opacity:0;transition:opacity .2s}
.card:hover .card-actions,.card.fav .card-actions{opacity:1}
.card-btn{background:none;border:none;cursor:pointer;padding:3px 5px;border-radius:4px;font-size:13px;color:var(--muted);transition:all .15s;line-height:1;text-decoration:none;display:inline-flex;align-items:center}
.card-btn:hover{color:var(--text)}
.card-star.active{color:var(--gold)!important;opacity:1!important}
.card-star:hover{color:var(--gold)!important}
.card-del:hover{color:var(--accent)!important}
.card-top{display:flex;gap:9px;margin-bottom:8px;padding-right:52px}
.favicon{width:24px;height:24px;border-radius:5px;background:var(--surface2);display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;overflow:hidden}
.favicon img{width:100%;height:100%;object-fit:cover}
.card-title{font-size:13px;font-weight:600;color:var(--text);line-height:1.3;margin-bottom:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card-domain{font-family:'DM Mono',monospace;font-size:10px;color:var(--muted)}
.card-summary{font-size:12px;color:var(--muted);line-height:1.55;margin-bottom:9px}
.card-footer{display:flex;gap:4px;flex-wrap:wrap}
.badge{font-size:10px;font-weight:600;padding:2px 8px;border-radius:20px;background:rgba(139,92,246,.15);color:var(--purple2)}
.tag{font-size:10px;padding:2px 7px;border-radius:20px;background:var(--surface2);border:1px solid var(--border);color:var(--muted);font-family:'DM Mono',monospace}
/* Settings modal */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:200;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
.modal-overlay.hidden{display:none}
.modal{background:var(--bg2);border:1px solid var(--border);border-radius:16px;width:480px;max-width:calc(100vw - 40px);max-height:calc(100vh - 60px);overflow-y:auto;box-shadow:0 24px 60px rgba(0,0,0,.6)}
.modal-header{padding:18px 20px 0;display:flex;justify-content:space-between;align-items:center}
.modal-title{font-size:15px;font-weight:700}
.modal-close{background:none;border:none;color:var(--muted);cursor:pointer;font-size:18px;padding:4px;border-radius:6px;line-height:1}
.modal-close:hover{color:var(--text)}
.modal-body{padding:16px 20px 20px}
.setting-group{margin-bottom:18px}
.setting-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}
.provider-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
.provider-card{background:var(--surface);border:1.5px solid var(--border);border-radius:10px;padding:10px 12px;cursor:pointer;transition:all .2s}
.provider-card:hover{border-color:rgba(139,92,246,.4)}
.provider-card.selected{border-color:var(--purple);background:rgba(139,92,246,.08)}
.provider-card-name{font-size:13px;font-weight:600;margin-bottom:2px}
.provider-card-sub{font-size:11px;color:var(--muted)}
.field-group{margin-bottom:12px}
.field-label{font-size:12px;color:var(--muted);margin-bottom:5px;display:flex;justify-content:space-between;align-items:center}
.field-hint{font-size:10px;color:var(--muted);opacity:.7}
.field-input{width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-size:13px;font-family:'DM Mono',monospace;outline:none;transition:border-color .2s}
.field-input:focus{border-color:var(--purple)}
.field-input::placeholder{color:var(--muted);opacity:.6}
.field-select{width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-size:13px;outline:none;cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238b87aa' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 10px center}
.field-select:focus{border-color:var(--purple)}
.save-btn{width:100%;background:linear-gradient(135deg,var(--purple),var(--pink));border:none;border-radius:9px;padding:10px;color:#fff;font-size:14px;font-weight:600;cursor:pointer;transition:opacity .2s;margin-top:4px}
.save-btn:hover{opacity:.9}
.status-dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:5px}
.status-ok{background:var(--green)}
.status-warn{background:var(--gold)}
.ollama-note{background:rgba(139,92,246,.08);border:1px solid rgba(139,92,246,.2);border-radius:8px;padding:10px 12px;font-size:12px;color:var(--muted);line-height:1.5;margin-top:8px}
/* Toast */
.toast{position:fixed;bottom:16px;right:16px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:9px 14px;font-size:13px;z-index:999;box-shadow:0 8px 24px rgba(0,0,0,.5);transition:all .25s;transform:translateY(8px);opacity:0;pointer-events:none}
.toast.show{transform:translateY(0);opacity:1}
.prog{height:2px;background:linear-gradient(90deg,var(--purple),var(--pink));width:0;transition:width .3s;position:fixed;top:0;left:0;z-index:100}
.empty{text-align:center;padding:60px 30px;color:var(--muted);grid-column:1/-1}
.empty-icon{font-size:36px;margin-bottom:10px}
.empty h3{font-size:14px;color:var(--text);margin-bottom:5px}
.empty p{font-size:12px;line-height:1.6}
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
</style>
</head>
<body>
<div class="prog" id="prog"></div>

<header>
  <div class="logo">🧠 Bookmark Brain <span class="ver">v1.8</span></div>
  <div class="header-mid">
    <div class="provider-pill" onclick="openSettings()">
      <span class="provider-dot" id="provider-dot"></span>
      <span id="provider-label">Loading...</span>
    </div>
  </div>
  <div class="header-right">
    <div class="stats">
      <span class="stat"><b id="n-total">0</b> bookmarks</span>
      <span class="stat"><b id="n-cats">0</b> categories</span>
    </div>
    <button class="settings-btn" onclick="openSettings()" title="Settings">⚙️</button>
  </div>
</header>

<div class="search-bar">
  <input class="search-input" id="search" type="search" placeholder="Search titles, summaries, tags, domains..." autocomplete="off">
</div>

<div class="main">
  <aside class="sidebar">
    <div class="dropzone" id="dz">
      <div class="dz-icon">🔗</div>
      <div class="dz-text"><strong>Drop links here</strong>Browser bar or .webloc/.url</div>
    </div>
    <div class="sidebar-label">Quick</div>
    <button class="cat-btn fav-btn" id="fav-btn" onclick="toggleFavFilter()">★ Favourites <span class="cat-count" id="fav-count">0</span></button>
    <div class="sidebar-label" style="margin-top:3px">Categories</div>
    <div id="cats"></div>
  </aside>
  <main class="content"><div class="cards" id="cards"></div></main>
</div>

<!-- Settings Modal -->
<div class="modal-overlay hidden" id="modal-overlay" onclick="handleOverlayClick(event)">
  <div class="modal" id="modal">
    <div class="modal-header">
      <span class="modal-title">⚙️ Settings</span>
      <button class="modal-close" onclick="closeSettings()">✕</button>
    </div>
    <div class="modal-body">
      <div class="setting-group">
        <div class="setting-label">AI Provider</div>
        <div class="provider-grid" id="provider-grid"></div>
      </div>
      <div id="provider-config"></div>
      <button class="save-btn" onclick="saveSettings()">Save Settings</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const $=id=>document.getElementById(id);
function esc(s){const d=document.createElement('div');d.textContent=String(s??'');return d.innerHTML;}
const COLORS={YouTube:'#ef4444','X / Twitter':'#94a3b8',Instagram:'#ec4899',LinkedIn:'#3b82f6',Reddit:'#f97316',Facebook:'#6366f1',Business:'#8b5cf6',Tools:'#06b6d4',Development:'#3b82f6',Education:'#10b981',Marketing:'#f59e0b',Design:'#ec4899',Social:'#6366f1',Finance:'#84cc16',Entertainment:'#f97316',News:'#14b8a6',Health:'#22c55e',Travel:'#a855f7',Shopping:'#ef4444',Sports:'#0ea5e9','AI Tools':'#8b5cf6','AI Image & Video':'#a855f7',Reference:'#8b87aa',Other:'#8b87aa'};

const PROVIDER_MODELS = """ + provider_models_json + r""";
const PROVIDER_LABELS = """ + provider_labels_json + r""";
const PROVIDER_SUBS = {
  anthropic:'Claude Haiku / Sonnet / Opus',
  openai:'GPT-4o mini, GPT-4o',
  gemini:'Gemini Flash / Pro',
  groq:'Llama, Mixtral (fast)',
  ollama:'Runs locally — free'
};

let settings = """ + json.dumps(json.loads(json.dumps({"provider": settings["provider"], "providers": settings["providers"]}))) + r""";
let activeCat='', favOnly=false, searchTimer;

// ── Toast / Progress ──
function toast(msg){const t=$('toast');t.textContent=msg;t.className='toast show';clearTimeout(t._t);t._t=setTimeout(()=>t.classList.remove('show'),3200)}
function prog(n){$('prog').style.width=n+'%';if(n>=100)setTimeout(()=>$('prog').style.width='0',400)}

// ── Provider pill ──
function updateProviderPill(){
  const p=settings.provider;
  $('provider-label').textContent=PROVIDER_LABELS[p]||p;
}

// ── Bookmarks ──
async function loadBM(){
  const q=$('search').value.trim();
  const p=[];
  if(q)p.push('q='+encodeURIComponent(q));
  if(activeCat)p.push('category='+encodeURIComponent(activeCat));
  let bm=await fetch('/api/bookmarks'+(p.length?'?'+p.join('&'):'')).then(r=>r.json());
  if(favOnly)bm=bm.filter(b=>b.favourite);
  // n-total is updated by loadCats which always fetches unfiltered count
  if(!bm.length){
    $('cards').innerHTML=`<div class="empty"><div class="empty-icon">🔍</div><h3>${activeCat||favOnly||q?'No matches':'No bookmarks yet'}</h3><p>${activeCat||favOnly||q?'Try different terms.':'Drag links or .webloc files into the sidebar.'}</p></div>`;
    return;
  }
  $('cards').innerHTML=bm.map(b=>{
    const col=COLORS[b.category]||'#8b87aa';
    const tags=Array.isArray(b.tags)?b.tags:JSON.parse(b.tags||'[]');
    const fi=b.domain?`<img src="https://www.google.com/s2/favicons?domain=${esc(b.domain)}&sz=32" onerror="this.parentNode.innerHTML='🔗'" />`:'🔗';
    return`<div class="card${b.favourite?' fav':''}">
      <div class="card-actions">
        <button class="card-btn card-star${b.favourite?' active':''}" onclick="toggleFav(${b.id},event)">${b.favourite?'★':'☆'}</button>
        <a class="card-btn" href="${esc(b.url)}" target="_blank">↗</a>
        <button class="card-btn card-del" onclick="delBM(${b.id},event)">✕</button>
      </div>
      <div class="card-top">
        <div class="favicon">${fi}</div>
        <div style="min-width:0"><div class="card-title" title="${esc(b.title||b.url)}">${esc(b.title||b.url)}</div><div class="card-domain">${esc(b.domain||'')}</div></div>
      </div>
      <div class="card-summary">${esc(b.summary||'')}</div>
      <div class="card-footer">
        <span class="badge" style="background:${col}22;color:${col}">${esc(b.category||'Other')}</span>
        ${tags.slice(0,4).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}
      </div>
    </div>`;
  }).join('');
}

async function loadCats(){
  const cats=await fetch('/api/categories').then(r=>r.json());
  $('n-cats').textContent=cats.length;
  const total=cats.reduce((s,c)=>s+c.count,0);
  $('n-total').textContent=total;
  $('cats').innerHTML=`<button class="cat-btn${!activeCat&&!favOnly?' active':''}" onclick="setCat('')">All <span class="cat-count">${total}</span></button>`
    +cats.map(c=>`<button class="cat-btn${activeCat===c.category&&!favOnly?' active':''}" onclick="setCat(${JSON.stringify(c.category).replace(/"/g,'&quot;')})">${c.category}<span class="cat-count">${c.count}</span></button>`).join('');
}

async function updateFavCount(){
  try{
    const s=await fetch('/api/stats').then(r=>r.json());
    $('fav-count').textContent=s.favourites;
  }catch(e){}
}

function setCat(c){activeCat=c;favOnly=false;$('fav-btn').classList.remove('active');loadCats();loadBM();}
function toggleFavFilter(){favOnly=!favOnly;$('fav-btn').classList.toggle('active',favOnly);if(favOnly)activeCat='';loadCats();loadBM();}
async function toggleFav(id,e){e.stopPropagation();await fetch('/api/bookmarks/'+id+'/favourite',{method:'PUT'});loadBM();loadCats();updateFavCount();}
async function delBM(id,e){e.stopPropagation();await fetch('/api/bookmarks/'+id,{method:'DELETE'});loadBM();loadCats();updateFavCount();}

// ── Upload / Drop ──
async function upload(files){
  const valid=[...files].filter(f=>f.name.endsWith('.webloc')||f.name.endsWith('.url'));
  if(!valid.length){toast('Drop .webloc or .url files');return}
  prog(15);toast(`Processing ${valid.length} file${valid.length>1?'s':''}...`);
  const fd=new FormData();valid.forEach(f=>fd.append('files',f));
  prog(45);
  const res=await fetch('/api/upload',{method:'POST',body:fd}).then(r=>r.json());
  prog(100);
  const added=res.filter(r=>r.success).length,skip=res.filter(r=>r.skipped).length;
  toast(added?`✓ Added ${added}${skip?' · '+skip+' skipped':''}`:skip?`${skip} already saved`:'Nothing added');
  loadBM();loadCats();updateFavCount();
}

async function addUrl(url){
  prog(20);toast('Processing...');
  try{
    const r=await fetch('/api/add_url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
    const d=await r.json();prog(100);
    if(d.success)toast('✓ Added: '+d.title);
    else if(d.skipped)toast('Already saved');
    else toast('Error: '+(d.error||'unknown'));
    loadBM();loadCats();updateFavCount();
  }catch(e){prog(100);toast('Error: '+e.message);}
}

async function handleDrop(e){
  const dt=e.dataTransfer;
  const files=[...(dt.files||[])].filter(f=>f.name.endsWith('.webloc')||f.name.endsWith('.url'));
  if(files.length){await upload(files);return;}
  const url=(dt.getData('URL')||dt.getData('text/uri-list')||dt.getData('text/plain')||'').trim().split('\n')[0].trim();
  if(url&&url.startsWith('http')){await addUrl(url);return;}
}

const dz=$('dz');
['dragenter','dragover'].forEach(e=>dz.addEventListener(e,ev=>{ev.preventDefault();dz.classList.add('over')}));
['dragleave','drop'].forEach(e=>dz.addEventListener(e,ev=>{ev.preventDefault();dz.classList.remove('over')}));
dz.addEventListener('drop',handleDrop);
document.addEventListener('dragover',e=>e.preventDefault());
document.addEventListener('drop',e=>{e.preventDefault();handleDrop(e);});
$('search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(loadBM,300)});

// ── Settings Modal ──
let editingSettings = null;

function openSettings(){
  editingSettings = JSON.parse(JSON.stringify(settings));
  renderProviderGrid();
  renderProviderConfig(editingSettings.provider);
  $('modal-overlay').classList.remove('hidden');
}

function closeSettings(){
  $('modal-overlay').classList.add('hidden');
}

function handleOverlayClick(e){
  if(e.target===$('modal-overlay'))closeSettings();
}

function renderProviderGrid(){
  $('provider-grid').innerHTML=Object.entries(PROVIDER_LABELS).map(([id,label])=>`
    <div class="provider-card${editingSettings.provider===id?' selected':''}" onclick="selectProvider('${id}')">
      <div class="provider-card-name">${label}</div>
      <div class="provider-card-sub">${PROVIDER_SUBS[id]||''}</div>
    </div>`).join('');
}

function selectProvider(id){
  editingSettings.provider=id;
  renderProviderGrid();
  renderProviderConfig(id);
}

function renderProviderConfig(provider){
  const cfg=editingSettings.providers[provider]||{};
  const models=PROVIDER_MODELS[provider]||[];
  const modelOpts=models.map(m=>`<option value="${m}"${cfg.model===m?' selected':''}>${m}</option>`).join('');

  let html='';

  if(provider==='ollama'){
    html+=`<div class="field-group">
      <div class="field-label">Ollama Base URL <span class="field-hint">default: http://localhost:11434</span></div>
      <input class="field-input" id="cfg-base-url" value="${cfg.base_url||'http://localhost:11434'}" placeholder="http://localhost:11434">
    </div>
    <div class="ollama-note">
      🦙 Ollama runs AI models completely locally on your Mac — no API key needed and totally free.<br><br>
      Install from <strong>ollama.com</strong>, then run a model:<br>
      <code style="font-family:'DM Mono',monospace;font-size:11px">ollama pull llama3.2</code>
    </div>`;
  } else {
    html+=`<div class="field-group">
      <div class="field-label">API Key</div>
      <input class="field-input" id="cfg-api-key" type="password" value="${cfg.api_key||''}" placeholder="Paste your API key here...">
    </div>`;
  }

  html+=`<div class="field-group">
    <div class="field-label">Model</div>
    <select class="field-select" id="cfg-model">${modelOpts}</select>
  </div>`;

  $('provider-config').innerHTML=html;
}

async function saveSettings(){
  const p=editingSettings.provider;
  const cfg=editingSettings.providers[p];
  if($('cfg-model')) cfg.model=$('cfg-model').value;
  if($('cfg-api-key')) cfg.api_key=$('cfg-api-key').value.trim();
  if($('cfg-base-url')) cfg.base_url=$('cfg-base-url').value.trim();

  const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(editingSettings)});
  const d=await r.json();
  if(d.success){
    settings=editingSettings;
    updateProviderPill();
    closeSettings();
    toast('✓ Settings saved');
  } else {
    toast('Error saving: '+(d.error||'unknown'));
  }
}

// ── Init ──
updateProviderPill();
loadBM();loadCats();updateFavCount();
</script>
</body>
</html>"""

# ── HTTP Handler ──────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send_json(self, data, status=200):
        b = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        path = self.path.split("?")[0]
        qs = self.path[len(path)+1:] if "?" in self.path else ""

        if path in ("/","/index.html"):
            s = load_settings()
            b = build_html(s).encode()
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(b)))
            self.end_headers(); self.wfile.write(b)

        elif path == "/api/bookmarks":
            params={}
            for p in qs.split("&"):
                if "=" in p:
                    k,v=p.split("=",1); params[k]=unquote(v.replace("+"," "))
            q=params.get("q","").strip(); cat=params.get("category","").strip()
            sql="SELECT * FROM bookmarks WHERE 1=1"; args=[]
            if q:
                sql+=" AND (title LIKE ? OR summary LIKE ? OR tags LIKE ? OR domain LIKE ?)"
                like=f"%{q}%"; args+=[like]*4
            if cat:
                sql+=" AND category = ?"; args.append(cat)
            sql+=" ORDER BY favourite DESC, LOWER(title) ASC"
            with _db_lock:
                db=get_db(); rows=[dict(r) for r in db.execute(sql,args).fetchall()]; db.close()
            for b in rows:
                try: b["tags"]=json.loads(b["tags"] or "[]")
                except: b["tags"]=[]
            self.send_json(rows)

        elif path == "/api/categories":
            with _db_lock:
                db=get_db(); rows=[dict(r) for r in db.execute("SELECT category, COUNT(*) as count FROM bookmarks GROUP BY category ORDER BY count DESC").fetchall()]; db.close()
            self.send_json(rows)

        elif path == "/api/stats":
            with _db_lock:
                db=get_db()
                total=db.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
                fav=db.execute("SELECT COUNT(*) FROM bookmarks WHERE favourite=1").fetchone()[0]
                db.close()
            self.send_json({"total":total,"favourites":fav})

        elif path == "/api/settings":
            self.send_json(load_settings())

        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        ct=self.headers.get("Content-Type","")
        cl=int(self.headers.get("Content-Length",0))

        if self.path == "/api/settings":
            body=json.loads(self.rfile.read(cl))
            save_settings(body)
            self.send_json({"success":True}); return

        if self.path == "/api/add_url":
            body=json.loads(self.rfile.read(cl))
            url=(body.get("url") or "").strip()
            if not url or not url.startswith("http"):
                self.send_json({"error":"Invalid URL"},400); return
            with _db_lock:
                db=get_db()
                exists=db.execute("SELECT id FROM bookmarks WHERE url=?",(url,)).fetchone()
                db.close()
            if exists:
                self.send_json({"error":"Already saved","skipped":True}); return
            try:
                data=analyze_bookmark(url,title=body.get("title",""))
                domain=urlparse(url).netloc.replace("www.","")
                with _db_lock:
                    db=get_db()
                    db.execute("INSERT INTO bookmarks (url,title,summary,category,tags,domain) VALUES (?,?,?,?,?,?)",
                        (url,data["title"],data["summary"],data["category"],json.dumps(data.get("tags",[])),domain))
                    db.commit(); db.close()
                self.send_json({"success":True,"title":data["title"],"category":data["category"]}); return
            except urllib.error.HTTPError as e:
                self.send_json({"error":f"API {e.code}: {e.read().decode()[:300]}"},500); return
            except Exception as e:
                self.send_json({"error":str(e)},500); return

        if self.path == "/api/upload":
            if "multipart/form-data" not in ct:
                self.send_json({"error":"Expected multipart"},400); return
            files=parse_multipart(self.rfile,ct,cl); results=[]
            for filename,file_content in files:
                url=extract_url(filename,file_content)
                if not url or not url.startswith("http"):
                    results.append({"filename":filename,"error":"No URL","skipped":True}); continue
                # Check duplicate — lock only for the DB read
                with _db_lock:
                    db=get_db()
                    already=db.execute("SELECT id FROM bookmarks WHERE url=?",(url,)).fetchone()
                    db.close()
                if already:
                    results.append({"filename":filename,"url":url,"error":"Already saved","skipped":True}); continue
                # Call AI outside the lock so searches/browses still work during upload
                try:
                    data=analyze_bookmark(url,title=Path(filename).stem)
                    domain=urlparse(url).netloc.replace("www.","")
                    with _db_lock:
                        db=get_db()
                        db.execute("INSERT INTO bookmarks (url,title,summary,category,tags,domain) VALUES (?,?,?,?,?,?)",
                            (url,data["title"],data["summary"],data["category"],json.dumps(data.get("tags",[])),domain))
                        db.commit(); db.close()
                    results.append({"filename":filename,"url":url,"title":data["title"],"success":True})
                except Exception as e:
                    results.append({"filename":filename,"url":url,"error":str(e),"skipped":True})
            self.send_json(results); return

        self.send_response(404); self.end_headers()

    def do_PUT(self):
        m=re.match(r'/api/bookmarks/(\d+)/favourite$',self.path)
        if m:
            bid=int(m.group(1))
            with _db_lock:
                db=get_db()
                row=db.execute("SELECT favourite FROM bookmarks WHERE id=?",(bid,)).fetchone()
                if row:
                    nv=0 if row["favourite"] else 1
                    db.execute("UPDATE bookmarks SET favourite=? WHERE id=?",(nv,bid))
                    db.commit(); db.close(); self.send_json({"success":True,"favourite":nv})
                else:
                    db.close(); self.send_json({"error":"Not found"},404)
        else:
            self.send_response(404); self.end_headers()

    def do_DELETE(self):
        m=re.match(r'/api/bookmarks/(\d+)$',self.path)
        if m:
            with _db_lock:
                db=get_db(); db.execute("DELETE FROM bookmarks WHERE id=?",(int(m.group(1)),)); db.commit(); db.close()
            self.send_json({"success":True})
        else:
            self.send_response(404); self.end_headers()

    def do_PATCH(self):
        m=re.match(r'/api/bookmarks/(\d+)$',self.path)
        if m:
            body=json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
            with _db_lock:
                db=get_db()
                if "category" in body: db.execute("UPDATE bookmarks SET category=? WHERE id=?",(body["category"],int(m.group(1))))
                if "tags" in body: db.execute("UPDATE bookmarks SET tags=? WHERE id=?",(json.dumps(body["tags"]),int(m.group(1))))
                db.commit(); db.close()
            self.send_json({"success":True})
        else:
            self.send_response(404); self.end_headers()


if __name__ == "__main__":
    os.makedirs(SUPPORT_DIR, exist_ok=True)
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"\n🧠 Bookmark Brain v1.8 — http://localhost:{PORT}")
    print(f"📁 {DB_PATH}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
