import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mac_launcher as launcher

class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        launcher.app.SUPPORT_DIR=self.temp.name
        launcher.app.DB_PATH=str(Path(self.temp.name)/'bookmarks.db')
        launcher.app.SETTINGS_PATH=str(Path(self.temp.name)/'settings.json')
        launcher.app.PORT=0
        self.service=launcher.LocalService()
    def tearDown(self):
        self.service.stop()
        self.temp.cleanup()
    def test_single_instance_and_relaunch(self):
        self.assertTrue(self.service.start())
        second=launcher.LocalService()
        self.assertFalse(second.start())
        self.assertEqual(second.url,self.service.url)
        self.service.stop()
        self.assertTrue(second.start())
        second.stop()
    def test_occupied_port_is_not_killed(self):
        import socket
        with socket.socket() as other:
            other.bind(('127.0.0.1',0));other.listen()
            launcher.app.PORT=other.getsockname()[1]
            self.assertTrue(self.service.start())
            self.assertNotEqual(self.service.server.server_address[1],launcher.app.PORT)
            self.assertEqual(other.getsockname()[1],launcher.app.PORT)
    def test_packaged_smoke_contract(self):
        launcher.smoke_test()

if __name__=='__main__':unittest.main()
