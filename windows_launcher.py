"""Windows launcher with a small control window; no Terminal required."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import urllib.request
import webbrowser

# Windows keeps application data outside the downloaded program folder.
os.environ.setdefault('BOOKMARK_SUPPORT', str(Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'BookmarkBrain'))
import app


class LocalService:
    def __init__(self):
        self.server = self.thread = self.mutex = self.url = None

    def start(self):
        folder = Path(app.SUPPORT_DIR)
        folder.mkdir(parents=True, exist_ok=True)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self.kernel = kernel
        name = 'Local\\BookmarkBrain-' + hashlib.sha256(str(folder.resolve()).lower().encode()).hexdigest()[:24]
        self.mutex = kernel.CreateMutexW(None, False, name)
        error = ctypes.get_last_error()
        if not self.mutex:
            raise ctypes.WinError(error)
        if error == 183:
            kernel.CloseHandle(self.mutex)
            self.mutex = None
            try:
                port = json.loads((folder / 'windows-port.json').read_text())['port']
                if isinstance(port, int) and 1024 <= port <= 65535:
                    self.url = f'http://127.0.0.1:{port}'
            except (OSError, ValueError, KeyError):
                pass
            return False
        try:
            try:
                self.server = app.ThreadingHTTPServer(('127.0.0.1', app.PORT), app.Handler)
            except OSError as error:
                if error.winerror != 10048 and error.errno != 10048:
                    raise
                self.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
            port = self.server.server_address[1]
            self.url = f'http://127.0.0.1:{port}'
            (folder / 'windows-port.json').write_text(json.dumps({'port': port}))
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            return True
        except Exception:
            self.stop()
            raise

    def stop(self):
        if self.server:
            if self.thread:
                self.server.shutdown()
                self.thread.join(timeout=5)
            self.server.server_close()
            self.server = None
        if self.mutex:
            self.kernel.CloseHandle(self.mutex)
            self.mutex = None


def control_window(service, smoke=False):
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.title('Bookmark Brain')
    root.geometry('410x220')
    ttk.Label(root, text='Bookmark Brain is running', font=('Segoe UI', 15)).pack(pady=18)
    ttk.Label(root, text='Minimise this window to keep saving bookmarks.\nClosing it quits the app.', justify='center').pack(pady=5)
    ttk.Button(root, text='Open Bookmark Brain', command=lambda: webbrowser.open(service.url)).pack(pady=5)
    ttk.Button(root, text='Open data folder', command=lambda: os.startfile(app.SUPPORT_DIR)).pack(pady=5)
    ttk.Button(root, text='Quit Bookmark Brain', command=root.destroy).pack(pady=5)
    if smoke:
        root.after(500, root.destroy)
    root.mainloop()


def smoke_test():
    with tempfile.TemporaryDirectory(prefix='bookmark-brain-windows-test-') as folder:
        app.SUPPORT_DIR = folder
        app.DB_PATH = str(Path(folder) / 'bookmarks.db')
        app.SETTINGS_PATH = str(Path(folder) / 'settings.json')
        app.PORT = 0
        service = LocalService()
        try:
            assert service.start()
            def request(path, body=None):
                headers = {'X-Bookmark-Token': app.SESSION_TOKEN, 'Content-Type': 'application/json'}
                req = urllib.request.Request(service.url + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
                with urllib.request.urlopen(req) as res:
                    return json.load(res)
            for count in range(3):
                result = request('/api/add_url', {'url': 'https://example.com/windows'})
            assert result['favourite']
            assert len(request('/api/bookmarks')) == 1
            assert request('/api/backup', {})['filename']
            second = LocalService()
            assert not second.start() and second.url == service.url
            control_window(service, smoke=True)
        finally:
            service.stop()
        # Released mutex and database survive reopening.
        again = LocalService()
        try:
            assert again.start()
        finally:
            again.stop()


def main():
    if '--smoke-test' in sys.argv:
        smoke_test()
        return
    service = LocalService()
    try:
        if not service.start():
            if service.url:
                webbrowser.open(service.url)
            return
        webbrowser.open(service.url)
        control_window(service)
    except Exception:
        from tkinter import messagebox
        messagebox.showerror('Bookmark Brain', 'Could not start. Check that your local data folder is writable. Your bookmarks have not been removed.')
        raise
    finally:
        service.stop()


if __name__ == '__main__':
    main()
