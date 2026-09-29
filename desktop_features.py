"""Local library maintenance and explicit provider discovery. Standard library only."""
import contextlib
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request
import urllib.error
from urllib.parse import quote, urlencode, urlparse


class BookmarkHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.current = None
    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            self.current = {'url': dict(attrs).get('href', ''), 'title': ''}
    def handle_data(self, data):
        if self.current is not None:
            self.current['title'] += data
    def handle_endtag(self, tag):
        if tag.lower() == 'a' and self.current is not None:
            self.rows.append(self.current)
            self.current = None


def parse_import(filename, content, valid_url, local_backup=False):
    if len(content) > (100_000_000 if local_backup else 2_000_000):
        raise ValueError('Choose a file smaller than 2 MB.')
    text = content.decode('utf-8-sig')
    if Path(filename).suffix.lower() in ('.html', '.htm'):
        parser = BookmarkHTML()
        parser.feed(text)
        source = parser.rows
    elif Path(filename).suffix.lower() == '.json':
        source = json.loads(text)
        if isinstance(source, dict):
            source = source.get('bookmarks')
    else:
        raise ValueError('Choose a browser HTML export or Bookmark Brain JSON file.')
    if not isinstance(source, list) or len(source) > (100000 if local_backup else 10000):
        raise ValueError('Choose a list containing up to 10,000 bookmarks.')
    rows, skipped = [], 0
    for value in source:
        if not isinstance(value, dict) or not valid_url(value.get('url')):
            skipped += 1
            continue
        tags = value.get('tags', [])
        if isinstance(tags, str):
            try: tags = json.loads(tags)
            except ValueError: tags = []
        rows.append({
            'url': value['url'],
            'title': str(value.get('title') or urlparse(value['url']).hostname)[:300],
            'summary': str(value.get('summary') or '')[:4000],
            'category': str(value.get('category') or 'Other')[:60],
            'tags': [t[:40] for t in tags if isinstance(t, str)][:20] if isinstance(tags, list) else [],
            'favourite': int(value.get('favourite') is True or value.get('favourite') == 1),
            'ai_enriched': value.get('ai_enriched') if type(value.get('ai_enriched')) in (int, bool) and value.get('ai_enriched') in (0, 1) else None,
            'save_count': min(1000000, max(1, value.get('save_count', 1))) if type(value.get('save_count', 1)) is int else 1,
            'added_at': str(value.get('added_at') or value.get('created_at') or datetime.now(timezone.utc).isoformat())[:40],
        })
    return rows, skipped


def snapshot(db, support, reason='manual'):
    """Caller holds the application DB lock. Writes private, atomic JSON, no keys."""
    folder = Path(support) / 'backups'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if reason == 'daily' and any(folder.glob(f'bookmarks-{day}-daily-*.json')):
        return None
    name = f'bookmarks-{day}-{reason}-{datetime.now(timezone.utc).strftime("%H%M%S-%f")}.json'
    rows = [dict(r) for r in db.execute('SELECT * FROM bookmarks ORDER BY id')]
    for row in rows:
        try: row['tags'] = json.loads(row['tags'] or '[]')
        except (ValueError, TypeError): row['tags'] = []
    fd, temporary = tempfile.mkstemp(dir=folder, prefix='.backup-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump({'format':'bookmark-brain-v1', 'bookmarks':rows}, f, ensure_ascii=False)
        os.replace(temporary, folder / name)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return name


def merge_rows(db, rows):
    added = 0
    for row in rows:
        result = db.execute('INSERT OR IGNORE INTO bookmarks (url,title,summary,category,tags,domain,favourite,added_at,save_count,ai_enriched) VALUES (?,?,?,?,?,?,?,?,?,?)',
            (row['url'],row['title'],row['summary'],row['category'],json.dumps(row['tags']),urlparse(row['url']).hostname,row['favourite'],row['added_at'],row['save_count'],row['ai_enriched']))
        added += result.rowcount
    db.commit()
    return added


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Provider redirected the request. Check the provider configuration.')


def provider_get(url, headers):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=20) as response:
        data = response.read(8_000_001)
        if len(data) > 8_000_000:
            raise ValueError('Provider model catalogue is too large.')
        return json.loads(data)


def model_catalogue(provider, cfg):
    key = cfg.get('api_key', '')
    if provider not in ('none', 'ollama', 'openrouter') and not key:
        raise ValueError('Enter an API key first.')
    bearer = {'Authorization': 'Bearer ' + key} if key else {}
    rows = []
    if provider == 'none': return []
    if provider == 'openrouter':
        data = provider_get('https://openrouter.ai/api/v1/models', bearer)
        rows = [{'id':r['id'], 'name':r.get('name',r['id'])} for r in data['data'] if 'text' in r.get('architecture',{}).get('output_modalities',[]) and 'text' in r.get('architecture',{}).get('input_modalities',[])]
    elif provider in ('openai', 'groq'):
        host = 'https://api.openai.com/v1/models' if provider == 'openai' else 'https://api.groq.com/openai/v1/models'
        data = provider_get(host, bearer)
        for r in data['data']:
            model = r['id']
            if provider == 'openai' and (not re.match(r'^(gpt-[456789]|o[1-9])',model) or any(x in model for x in ('audio','realtime','transcribe','image','tts','search','instruct'))): continue
            if provider == 'groq' and (r.get('active') is False or any(x in model for x in ('whisper','tts','guard'))): continue
            rows.append({'id':model,'name':model})
    elif provider == 'anthropic':
        after = None
        for _ in range(10):
            query = {'limit':100}
            if after: query['after_id'] = after
            data = provider_get('https://api.anthropic.com/v1/models?' + urlencode(query), {'x-api-key':key,'anthropic-version':'2023-06-01'})
            rows.extend({'id':r['id'],'name':r.get('display_name',r['id'])} for r in data['data'])
            if not data.get('has_more'): break
            after = data.get('last_id')
            if not after: break
    elif provider == 'gemini':
        token = None
        for _ in range(10):
            query = {'pageSize':1000}
            if token: query['pageToken'] = token
            data = provider_get('https://generativelanguage.googleapis.com/v1beta/models?' + urlencode(query), {'x-goog-api-key':key})
            rows.extend({'id':r['name'].removeprefix('models/'),'name':r.get('displayName',r['name'])} for r in data.get('models',[]) if 'generateContent' in r.get('supportedGenerationMethods',[]))
            token = data.get('nextPageToken')
            if not token: break
    elif provider == 'ollama':
        base = cfg.get('base_url','http://localhost:11434').rstrip('/')
        u = urlparse(base)
        if u.scheme not in ('http','https') or u.hostname not in ('localhost','127.0.0.1','::1') or u.username or u.password:
            raise ValueError('Ollama must use a local loopback address.')
        data = provider_get(base + '/api/tags', {})
        rows = [{'id':r['name'],'name':r['name']} for r in data.get('models',[])]
    else: raise ValueError('Unknown provider.')
    return sorted({r['id']: {'id':str(r['id'])[:200], 'name':str(r['name'])[:200]} for r in rows}.values(), key=lambda r:r['id'])[:3000]
