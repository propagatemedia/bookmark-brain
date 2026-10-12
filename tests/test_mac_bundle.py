"""Deployment parsing must not silently lower a bundle's requirements."""
import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('mac_bundle', Path(__file__).resolve().parents[1] / 'scripts/mac_bundle.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DeploymentTests(unittest.TestCase):
    def test_highest_minimum_numeric(self):
        self.assertEqual(module.deployment_minimum(' minos 11.0\n minos 12.3\n minos 9.9\n'), '12.3')

    def test_linker_version_is_not_os(self):
        self.assertEqual(module.deployment_minimum(' cmd LC_BUILD_VERSION\n minos 11.0\n tool LD\n version 1267.0\n'), '11.0')

    def test_legacy_command(self):
        self.assertEqual(module.deployment_minimum(' cmd LC_VERSION_MIN_MACOSX\n version 10.13\n sdk 15.0\n'), '10.13')

    def test_missing_target_rejected(self):
        with self.assertRaises(ValueError):
            module.deployment_minimum(' sdk 26.0\n')
