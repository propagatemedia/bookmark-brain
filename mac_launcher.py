"""Terminal-free macOS launcher. Owns only the server it starts."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import sys
import threading
import urllib.request
import webbrowser

import app


class LocalService:
    def __init__(self):
        self.server = None
        self.thread = None
        self.lock = None
        self.url = None

    def start(self):
        support = Path(app.SUPPORT_DIR)
        support.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = open(support / 'desktop.lock', 'a+')
        os.chmod(support / 'desktop.lock', 0o600)
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.seek(0)
            try:
                port = json.loads(self.lock.read())['port']
                if isinstance(port, int) and 1024 <= port <= 65535:
                    self.url = f'http://127.0.0.1:{port}'
            except (ValueError, KeyError):
                pass
            self.lock.close()
            self.lock = None
            return False
        try:
            try:
                self.server = app.ThreadingHTTPServer(('127.0.0.1', app.PORT), app.Handler)
            except OSError as error:
                import errno
                if error.errno != errno.EADDRINUSE:
                    raise
                self.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
            port = self.server.server_address[1]
            self.url = f'http://127.0.0.1:{port}'
            self.lock.seek(0)
            self.lock.truncate()
            json.dump({'port': port}, self.lock)
            self.lock.flush()
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            return True
        except Exception:
            self.stop()
            raise

    def stop(self):
        if self.server is not None:
            if self.thread is not None:
                self.server.shutdown()
                self.thread.join(timeout=5)
            self.server.server_close()
            self.server = None
        if self.lock is not None:
            self.lock.seek(0)
            self.lock.truncate()
            fcntl.flock(self.lock, fcntl.LOCK_UN)
            self.lock.close()
            self.lock = None


def smoke_test():
    import tempfile
    with tempfile.TemporaryDirectory(prefix='bookmark-brain-bundle-test-') as folder:
        app.SUPPORT_DIR = folder
        app.DB_PATH = str(Path(folder) / 'bookmarks.db')
        app.SETTINGS_PATH = str(Path(folder) / 'settings.json')
        app.PORT = 0
        service = LocalService()
        try:
            assert service.start()
            with urllib.request.urlopen(service.url) as response:
                html = response.read().decode()
                assert '<title>Bookmark Brain' in html
                assert '<title>🧠' not in html
            headers = {'X-Bookmark-Token': app.SESSION_TOKEN, 'Content-Type': 'application/json'}
            request = urllib.request.Request(service.url + '/api/add_url', data=json.dumps({'url':'https://example.com/bundle-test'}).encode(), headers=headers)
            with urllib.request.urlopen(request) as response:
                assert json.load(response)['success']
            request = urllib.request.Request(service.url + '/api/bookmarks', headers=headers)
            with urllib.request.urlopen(request) as response:
                rows = json.load(response)
                assert len(rows) == 1
                bid = rows[0]['id']
            def send(path, body, method='POST'):
                req = urllib.request.Request(service.url + path, data=json.dumps(body).encode(), headers=headers, method=method)
                with urllib.request.urlopen(req) as response:
                    return json.load(response)
            send('/api/add_url', {'url':'https://example.com/bundle-test'})
            assert send('/api/add_url', {'url':'https://example.com/bundle-test'})['favourite']
            send('/api/bookmarks/' + str(bid), {'title':'Edited in bundle','summary':'Local notes','tags':['tested']}, 'PATCH')
            result = send('/api/import', {'filename':'browser.html','content':'<A HREF="https://example.org/import">Imported</A>'})
            assert result['added'] == 1
            assert send('/api/backup', {})['filename']
            assert send('/api/models', {'provider':'none'})['models'] == []
            second = LocalService()
            assert second.start() is False
            assert second.url == service.url
        finally:
            service.stop()
    if sys.stdout:
        print('BUNDLE_SMOKE_TEST_PASSED')


def main():
    if '--smoke-test' in sys.argv:
        smoke_test()
        return
    import rumps
    service = LocalService()
    try:
        if not service.start():
            if service.url:
                webbrowser.open(service.url)
            else:
                rumps.alert('Bookmark Brain is starting', 'Please try opening the app again in a moment.')
            return
        class BookmarkBrainMenu(rumps.App):
            def __init__(self):
                super().__init__('Bookmark Brain', title='🧠', quit_button=None)
                self.menu = [rumps.MenuItem('Open Bookmark Brain', callback=self.open_library),
                             rumps.MenuItem('Open data folder', callback=self.open_data),
                             None, rumps.MenuItem('Quit Bookmark Brain', callback=self.quit)]

            def open_library(self, _):
                webbrowser.open(service.url)

            def open_data(self, _):
                import subprocess
                subprocess.Popen(['/usr/bin/open', app.SUPPORT_DIR])

            def quit(self, _):
                service.stop()
                rumps.quit_application()

        menu = BookmarkBrainMenu()
        if os.environ.get('BOOKMARK_NO_BROWSER') != '1':
            webbrowser.open(service.url)
        # Automated UI lifecycle check uses an isolated support directory.
        test_seconds = os.environ.get('BOOKMARK_TEST_EXIT_SECONDS')
        if test_seconds and os.environ.get('BOOKMARK_SUPPORT', '').startswith('/tmp/'):
            timer = rumps.Timer(lambda _: menu.quit(None), int(test_seconds))
            timer.start()
        menu.run()
    except Exception:
        rumps.alert('Bookmark Brain could not start', 'Please check that your local data folder is writable, then try opening the app again. Your bookmarks have not been removed.')
        raise
    finally:
        service.stop()


if __name__ == '__main__':
    main()
