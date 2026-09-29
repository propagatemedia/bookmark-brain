import json
from pathlib import Path
from unittest.mock import patch
import unittest
import test_app
app = test_app.app
import desktop_features as features

class FeatureTests(unittest.TestCase):
    setUp = test_app.DesktopTests.setUp
    tearDown = test_app.DesktopTests.tearDown
    request = test_app.DesktopTests.request
    def test_enrichment_status_failure_and_success(self):
        self.request('POST','/api/add_url',{'url':'https://example.com/enrich'})
        row=self.request('GET','/api/bookmarks')[1][0]
        self.assertEqual(row['ai_enriched'],0)
        route='/api/bookmarks/'+str(row['id'])+'/enrich'
        self.assertEqual(self.request('POST',route,{'confirm_cost':True})[0],400)
        settings=app.load_settings();settings['provider']='openrouter';settings['providers']['openrouter']['model']='fixture';app.save_settings(settings)
        self.assertEqual(self.request('POST',route,{})[0],400)
        with patch.object(app,'analyze_bookmark',return_value={'notice':'Limited'}):
            self.assertFalse(self.request('POST',route,{'confirm_cost':True})[1]['success'])
        self.assertEqual(self.request('GET','/api/bookmarks')[1][0],row)
        enriched={'title':'Enriched','summary':'AI notes','category':'Tools','tags':['ai'],'ai_enriched':True}
        with patch.object(app,'analyze_bookmark',return_value=enriched) as call:
            self.assertTrue(self.request('POST',route,{'confirm_cost':True})[1]['success'])
            self.request('POST',route,{'confirm_cost':True})
            self.assertEqual(call.call_count,1)
        result=self.request('GET','/api/bookmarks')[1][0]
        self.assertEqual((result['ai_enriched'],result['summary']),(1,'AI notes'))
        rows,_=features.parse_import('backup.json',json.dumps([result]).encode(),app.valid_url)
        self.assertEqual(rows[0]['ai_enriched'],1)

    def test_rate_limit_saves_links_and_backs_off(self):
        settings=app.load_settings(); settings['provider']='openrouter'
        settings['providers']['openrouter']['model']='fixture'; app.save_settings(settings)
        error=app.urllib.error.HTTPError('https://provider.example',429,'secret',{'Retry-After':'120'},None)
        with patch.dict(app._ai_cooldowns,{},clear=True), patch.dict(app.CALLERS,{'openrouter':unittest.mock.Mock(side_effect=error)}), patch.object(app.time,'monotonic',return_value=100):
            for suffix in ('one','two','three'):
                status,result=self.request('POST','/api/add_url',{'url':'https://example.com/'+suffix})
                self.assertEqual(status,200)
                self.assertTrue(result['success'])
                self.assertIn('without AI',result['notice'])
                self.assertNotIn('secret',json.dumps(result))
            self.assertEqual(app.CALLERS['openrouter'].call_count,1)
            self.assertEqual(len(self.request('GET','/api/bookmarks')[1]),3)
            self.assertEqual(app._ai_cooldowns['openrouter'],220)
            with patch.object(app.time,'monotonic',return_value=221):
                self.request('POST','/api/add_url',{'url':'https://example.com/four'})
            self.assertEqual(app.CALLERS['openrouter'].call_count,2)

    def test_edit_persists_and_invalid_edit_is_atomic(self):
        self.request('POST','/api/add_url',{'url':'https://example.com'})
        bid=self.request('GET','/api/bookmarks')[1][0]['id']
        status,_=self.request('PATCH',f'/api/bookmarks/{bid}',{'title':'Changed','summary':'Notes','tags':['useful'],'category':'Work'})
        self.assertEqual(status,200)
        row=self.request('GET','/api/bookmarks')[1][0]
        self.assertEqual((row['title'],row['summary'],row['tags']),('Changed','Notes',['useful']))
        self.assertEqual(self.request('PATCH',f'/api/bookmarks/{bid}',{'title':'Not saved','tags':['x'*41]})[0],400)
        self.assertEqual(self.request('GET','/api/bookmarks')[1][0]['title'],'Changed')

    def test_third_save_favourites_without_duplicate(self):
        payload={'url':'https://example.com/repeated'}
        self.request('POST','/api/add_url',payload)
        self.assertEqual(self.request('POST','/api/add_url',payload)[1]['save_count'],2)
        self.assertEqual(self.request('GET','/api/bookmarks')[1][0]['favourite'],0)
        result=self.request('POST','/api/add_url',payload)[1]
        self.assertTrue(result['favourite'])
        rows=self.request('GET','/api/bookmarks')[1]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['save_count'],3)

    def test_browser_import_skips_unsafe_and_duplicates_without_ai(self):
        html='<DL><A HREF="https://example.com">A &amp; B</A><A HREF="javascript:alert(1)">Unsafe</A><A HREF="https://example.com">Again</A></DL>'
        with patch.object(app,'analyze_bookmark',side_effect=AssertionError('No AI on import')):
            status,result=self.request('POST','/api/import',{'filename':'Bookmarks.html','content':html})
        self.assertEqual(status,200)
        self.assertEqual((result['added'],result['skipped']),(1,2))
        row=self.request('GET','/api/bookmarks')[1][0]
        self.assertEqual(row['title'],'A & B')
        self.assertEqual(row['save_count'],1)

    def test_backup_restore_missing_keeps_existing_edits_and_secrets_out(self):
        self.request('POST','/api/add_url',{'url':'https://example.com/one'})
        self.request('POST','/api/add_url',{'url':'https://example.com/two'})
        filename=self.request('POST','/api/backup',{})[1]['filename']
        rows=self.request('GET','/api/bookmarks')[1]
        self.request('DELETE',f"/api/bookmarks/{rows[0]['id']}")
        self.request('PATCH',f"/api/bookmarks/{rows[1]['id']}",{'title':'Keep my edit'})
        status,result=self.request('POST','/api/restore',{'filename':filename})
        self.assertEqual(status,200)
        self.assertEqual(result['added'],1)
        self.assertIn('Keep my edit',[r['title'] for r in self.request('GET','/api/bookmarks')[1]])
        backups=list((Path(app.SUPPORT_DIR)/'backups').glob('*.json'))
        self.assertEqual(len([p for p in backups if '-daily-' in p.name]),1)
        self.assertNotIn('api_key',(Path(app.SUPPORT_DIR)/'backups'/filename).read_text())
        self.assertEqual(self.request('POST','/api/restore',{'filename':'../settings.json'})[0],400)

    def test_json_roundtrip_preserves_notes_tags_favourites(self):
        content=json.dumps([{'url':'https://example.com/a','title':'Title','summary':'Note','tags':'["tag"]','category':'Mine','favourite':1}])
        self.assertEqual(self.request('POST','/api/import',{'filename':'backup.json','content':content})[0],200)
        row=self.request('GET','/api/bookmarks')[1][0]
        self.assertEqual((row['summary'],row['tags'],row['favourite']),('Note',['tag'],1))

    def test_provider_discovery_uses_saved_key_without_returning_it(self):
        settings=app.load_settings();settings['providers']['openrouter']['api_key']='secret';app.save_settings(settings)
        with patch.object(features,'provider_get',return_value={'data':[{'id':'provider/text-model','name':'Model','architecture':{'input_modalities':['text'],'output_modalities':['text']}},{'id':'image','architecture':{'input_modalities':['text'],'output_modalities':['image']}}]}) as get:
            status,result=self.request('POST','/api/models',{'provider':'openrouter','config':{'api_key':''}})
        self.assertEqual(status,200)
        self.assertEqual(len(result['models']),1)
        self.assertEqual(get.call_args.args[1]['Authorization'],'Bearer secret')
        self.assertNotIn('secret',json.dumps(result))

    def test_model_test_needs_confirmation_and_uses_only_sample(self):
        body={'provider':'openrouter','config':{'api_key':'test','model':'provider/model'}}
        self.assertEqual(self.request('POST','/api/test-provider',body)[0],400)
        with patch.dict(app.CALLERS,{'openrouter':lambda prompt,cfg: {'title':'Example'} if 'example.com' in prompt else None}):
            self.assertEqual(self.request('POST','/api/test-provider',{**body,'confirm_cost':True})[0],200)
        self.assertEqual(self.request('GET','/api/bookmarks')[1],[])

    def test_openai_uses_responses_without_legacy_temperature(self):
        response={'output':[{'type':'reasoning'},{'type':'message','content':[{'type':'output_text','text':'{"title":"Example"}'}]}]}
        with patch.object(app,'http_post',return_value=response) as post:
            self.assertEqual(app.call_openai('test',{'model':'gpt-test','api_key':'test'})['title'],'Example')
        self.assertTrue(post.call_args.args[0].endswith('/responses'))
        self.assertNotIn('temperature',post.call_args.args[2])
        self.assertFalse(post.call_args.args[2]['store'])

    def test_new_provider_merges_with_existing_settings(self):
        settings=app.load_settings();settings['providers'].pop('openrouter');settings['providers']['openai']['model']='existing-model';app.save_settings(settings)
        result=app.load_settings()
        self.assertIn('openrouter',result['providers'])
        self.assertEqual(result['providers']['openai']['model'],'existing-model')

    def test_old_database_upgrade_preserves_bookmarks(self):
        import sqlite3
        with sqlite3.connect(app.DB_PATH) as db:
            db.execute('CREATE TABLE bookmarks (id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL, title TEXT, summary TEXT, category TEXT, tags TEXT, domain TEXT, favourite INTEGER DEFAULT 0, added_at TEXT)')
            db.execute('INSERT INTO bookmarks VALUES (1,?,?,?,?,?,?,?,?)',('https://example.com/legacy','My original title','My notes','Work','["old"]','example.com',1,'2026-01-01'))
        status,rows=self.request('GET','/api/bookmarks')
        self.assertEqual(status,200)
        self.assertEqual((rows[0]['title'],rows[0]['summary'],rows[0]['favourite'],rows[0]['save_count']),('My original title','My notes',1,1))

    def test_model_catalogues_filter_and_paginate(self):
        with patch.object(features,'provider_get',side_effect=[{'data':[{'id':'claude-a'}],'has_more':True,'last_id':'claude-a'},{'data':[{'id':'claude-b'}],'has_more':False}]):
            self.assertEqual(len(features.model_catalogue('anthropic',{'api_key':'fixture'})),2)
        with patch.object(features,'provider_get',return_value={'models':[{'name':'models/text','supportedGenerationMethods':['generateContent']},{'name':'models/embed','supportedGenerationMethods':['embedContent']}]}):
            self.assertEqual(features.model_catalogue('gemini',{'api_key':'fixture'})[0]['id'],'text')
        with patch.object(features,'provider_get',return_value={'data':[{'id':'gpt-5-example'},{'id':'text-embedding-3-small'},{'id':'gpt-audio'}]}):
            self.assertEqual([r['id'] for r in features.model_catalogue('openai',{'api_key':'fixture'})],['gpt-5-example'])
        with patch.object(features,'provider_get',return_value={'models':[{'name':'local-model'}]}):
            self.assertEqual(features.model_catalogue('ollama',{'base_url':'http://127.0.0.1:11434'})[0]['id'],'local-model')

    def test_openrouter_request_and_provider_error_redaction(self):
        import urllib.error,io
        with patch.object(app,'http_post',return_value={'choices':[{'message':{'content':'{"title":"Example"}'}}]}) as post:
            self.assertEqual(app.call_openrouter('test',{'model':'vendor/model','api_key':'fixture'})['title'],'Example')
            self.assertEqual(post.call_args.args[0],'https://openrouter.ai/api/v1/chat/completions')
        failure=urllib.error.HTTPError('https://provider.example',401,'Bad key',{},io.BytesIO(b'secret-key-data'))
        with patch.object(features,'model_catalogue',side_effect=failure):
            status,result=self.request('POST','/api/models',{'provider':'openrouter'})
        self.assertEqual(status,502)
        self.assertIn('API key',result['error'])
        self.assertNotIn('secret',json.dumps(result))
