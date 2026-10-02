"""Regressionstests fuer Pfade, Pack-Kopie und den Neustart nach Updates."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dubforge_core as pc
import updater as upd


class SafeNameTests(unittest.TestCase):
    def test_dot_names_never_point_outside_packs(self):
        for name in (".", "..", "...", " . "):
            self.assertEqual(pc.safe_name(name, "Mein_Pack"), "Mein_Pack")

    def test_trailing_dots_and_device_names(self):
        self.assertEqual(pc.safe_name("My.Pack."), "My.Pack")
        self.assertEqual(pc.safe_name("CON"), "_CON")
        self.assertEqual(pc.safe_name("nul.txt"), "_nul.txt")
        self.assertEqual(pc.safe_name("Mein Pack"), "Mein_Pack")


class CopyPackTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.packs = os.path.join(self.root, "packs")
        self.pack = os.path.join(self.packs, "Szene")
        os.makedirs(self.pack)
        with open(os.path.join(self.pack, "01_a_0-000.wav"), "w") as f:
            f.write("audio")

    def test_target_is_own_folder_keeps_pack(self):
        self.assertEqual(os.path.normpath(pc.copy_pack(self.pack, self.packs)),
                         os.path.normpath(self.pack))
        self.assertTrue(os.path.isfile(os.path.join(self.pack, "01_a_0-000.wav")))

    def test_target_inside_pack_is_refused(self):
        with self.assertRaises(RuntimeError):
            pc.copy_pack(self.pack, self.pack)
        self.assertTrue(os.path.isfile(os.path.join(self.pack, "01_a_0-000.wav")))

    def test_normal_copy_replaces_old_copy(self):
        game = os.path.join(self.root, "game")
        os.makedirs(os.path.join(game, "Szene"))
        dest = pc.copy_pack(self.pack, game)
        self.assertTrue(os.path.isfile(os.path.join(dest, "01_a_0-000.wav")))


class UpdaterTests(unittest.TestCase):
    def test_restart_uses_running_python_not_bat(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        open(os.path.join(root, "Start DubForge.bat"), "w").close()
        open(os.path.join(root, "DubForge.pyw"), "w").close()
        cmd = upd._restart_command(root, "DubForge")
        self.assertNotIn(".bat", cmd)
        self.assertIn("DubForge.pyw", cmd)

    def test_installed_copy_drops_bat_and_skips_runtime(self):
        stage = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, stage, True)
        for rel in ("DubForge.pyw", "Setup.bat", "assets/dubstage.ico",
                    "runtime/Lib/os.py", "installer/make_icons.py"):
            path = os.path.join(stage, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w").close()
        self.assertEqual(upd.collect(stage),
                         ["DubForge.pyw", "Setup.bat", "assets/dubstage.ico"])
        self.assertEqual(sorted(upd.prune(stage, (".bat",))),
                         ["DubForge.pyw", "assets/dubstage.ico"])
        self.assertFalse(os.path.exists(os.path.join(stage, "Setup.bat")))


if __name__ == "__main__":
    unittest.main()
