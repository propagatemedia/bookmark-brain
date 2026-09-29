import contextlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('bookmark_app', Path(__file__).resolve().parents[1] / 'app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        app.SUPPORT_DIR = self.temp.name
        app.DB_PATH = str(Path(self.temp.name) / 'bookmarks.db')
        app.SETTINGS_PATH = str(Path(self.temp.name) / 'settings.json')
        app.DEFAULT_SETTINGS['providers']['anthropic']['api_key'] = ''
        self.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, method, path, body=None, headers=None, token=True):
        h = {'Content-Type': 'application/json'}
        if token: h['X-Bookmark-Token'] = app.SESSION_TOKEN
        h.update(headers or {})
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        c.request(method, path, json.dumps(body) if body is not None else None, h)
        r = c.getresponse()
        payload = r.read().decode()
        status = r.status
        c.close()
        return status, json.loads(payload) if payload.startswith(('[', '{')) else payload

    def test_save_search_favourite_export_delete_without_ai(self):
        with patch.object(app, 'http_post', side_effect=AssertionError('No network expected')):
            self.assertEqual(self.request('POST','/api/add_url',{'url':'https://github.com/test','title':'Example'})[0], 200)
        rows = self.request('GET','/api/bookmarks?q=Example')[1]
        self.assertEqual(len(rows),1)
        self.assertEqual(len(self.request('GET','/api/bookmarks?q=github.com%2Ftest')[1]),1)
        self.assertEqual(rows[0]['category'],'Development')
        bid = rows[0]['id']
        self.assertTrue(self.request('POST','/api/add_url',{'url':rows[0]['url']})[1]['skipped'])
        self.assertEqual(self.request('PUT',f'/api/bookmarks/{bid}/favourite')[0],200)
        self.assertEqual(self.request('GET','/api/bookmarks')[1][0]['favourite'],1)
        self.assertEqual(self.request('DELETE',f'/api/bookmarks/{bid}')[0],200)
        self.assertEqual(self.request('GET','/api/bookmarks')[1],[])

    def test_request_boundaries(self):
        self.assertEqual(self.request('GET','/api/settings',token=False)[0],403)
        self.assertEqual(self.request('GET','/',headers={'Host':'attacker.example'})[0],403)
        self.assertEqual(self.request('POST','/api/settings',{},headers={'Origin':'https://attacker.example'})[0],403)
        self.assertEqual(self.request('GET','/',headers={'Sec-Fetch-Site':'cross-site'})[0],403)
        self.assertEqual(self.request('POST','/api/add_url',{},headers={'Content-Length':'2000001'})[0],413)
        self.assertEqual(self.request('POST','/api/add_url',[],)[0],400)

    def test_secrets_masked_preserved_and_private_on_disk(self):
        settings=app.load_settings()
        settings['providers']['anthropic']['api_key']='secret-test-value'
        app.save_settings(settings)
        status, public=self.request('GET','/api/settings')
        self.assertEqual(status,200)
        self.assertNotIn('secret-test-value',json.dumps(public))
        self.assertTrue(public['providers']['anthropic']['has_key'])
        self.assertNotIn('secret-test-value',self.request('GET','/')[1])
        self.assertEqual(self.request('POST','/api/settings',public)[0],200)
        self.assertEqual(app.load_settings()['providers']['anthropic']['api_key'],'secret-test-value')
        self.assertEqual(os.stat(app.SETTINGS_PATH).st_mode & 0o777,0o600)
        public['providers']['anthropic']['clear_key']=True
        self.request('POST','/api/settings',public)
        self.assertEqual(app.load_settings()['providers']['anthropic']['api_key'],'')

    def test_settings_script_injection_and_remote_ollama_blocked(self):
        settings=app.load_settings()
        settings['providers']['ollama']['model']='</script><script>alert(1)</script>'
        html=app.build_html(settings)
        self.assertNotIn('</script><script>alert(1)',html)
        self.assertIn('\\u003c/script',html)
        settings['providers']['ollama']['base_url']='https://attacker.example'
        self.assertEqual(self.request('POST','/api/settings',settings)[0],400)

    def test_unsafe_links_and_malformed_metadata(self):
        for url in ('javascript:alert(1)','file:///tmp/foo','httpjunk','https://user:password@example.com','https://example.com\n'):
            self.assertEqual(self.request('POST','/api/add_url',{'url':url})[0],400)
        data=app.metadata({'tags':'not a list','title':'x'*1000},'https://example.com')
        self.assertEqual(data['tags'],[])
        self.assertEqual(len(data['title']),300)
        self.assertEqual(self.request('PATCH','/api/bookmarks/999',{'tags':[]})[0],404)

    def test_shortcut_import_and_partial_error(self):
        boundary='test-boundary'
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="Example.url"\r\n\r\n[InternetShortcut]\r\nURL=https://example.org/\r\n--{boundary}--\r\n').encode()
        c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=3)
        c.request('POST','/api/upload',body,{'Content-Type':f'multipart/form-data; boundary={boundary}','X-Bookmark-Token':app.SESSION_TOKEN})
        r=c.getresponse()
        self.assertEqual(r.status,200)
        self.assertTrue(json.loads(r.read())[0]['success'])
        c.close()
        self.assertEqual(len(self.request('GET','/api/bookmarks')[1]),1)

    def test_ai_failure_does_not_disclose_secrets_or_modify_library(self):
        settings=app.load_settings();settings['provider']='anthropic';app.save_settings(settings)
        with patch.dict(app.CALLERS,{'anthropic':lambda *_: (_ for _ in ()).throw(RuntimeError('secret-test-key'))}):
            status,body=self.request('POST','/api/add_url',{'url':'https://example.com'})
        self.assertEqual(status,502)
        self.assertNotIn('secret-test-key',json.dumps(body))
        self.assertEqual(self.request('GET','/api/bookmarks')[1],[])

if __name__=='__main__': unittest.main()
