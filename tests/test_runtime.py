"""Platform dispatch must keep frozen apps independent of the developer's PATH."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from desktop.runtime import bundled_node, default_data_dir, webview_gui


class RuntimeTest(unittest.TestCase):
    def test_windows_keeps_existing_data_and_engine(self):
        with patch("desktop.runtime.sys.platform", "win32"), patch.dict(os.environ, {"LOCALAPPDATA": "local-data"}):
            self.assertEqual(default_data_dir(), Path("local-data") / "Mystery")
            self.assertEqual(webview_gui(), "edgechromium")

    def test_mac_data_and_engine(self):
        with patch("desktop.runtime.sys.platform", "darwin"), patch("desktop.runtime.Path.home", return_value=Path("user-home")):
            self.assertEqual(default_data_dir(), Path("user-home/Library/Application Support/Mystery"))
            self.assertEqual(webview_gui(), "cocoa")

    def test_frozen_node_uses_platform_binary_and_missing_falls_back(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "runtime").mkdir()
            with patch("desktop.runtime.sys._MEIPASS", str(root), create=True):
                for platform, name in (("win32", "node.exe"), ("darwin", "node")):
                    with patch("desktop.runtime.sys.platform", platform):
                        self.assertIsNone(bundled_node())
                        binary = root / "runtime" / name
                        binary.write_bytes(b"runtime-placeholder")
                        self.assertEqual(bundled_node(), str(binary))
                        binary.unlink()
