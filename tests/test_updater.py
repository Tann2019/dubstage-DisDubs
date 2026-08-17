# -*- coding: utf-8 -*-
"""
Tests fuer den Selbst-Update / tests for the in-app updater.

Der Tausch selbst wird in einem Sandkasten wirklich ausgefuehrt: eine
kurzlebige App wird gestartet, das Skript wartet auf ihr Ende, kopiert und
haette danach neu gestartet. Genau das ist einmal stehen geblieben - eine
Pipe (tasklist | find) bleibt in einem Prozess ohne Konsole haengen, das
Update kam nie an und ein Fenster stand herum.

The swap is really carried out in a sandbox: a short-lived stand-in app is
started, the script waits for it to end, copies, and would restart it.
That is what once hung - a pipe (tasklist | find) blocks in a process
without a console, the update never arrived and a window sat there.
"""

import io
import os
import sys
import time
import shutil
import tempfile
import unittest
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import updater as upd  # noqa: E402

IS_WINDOWS = os.name == "nt"


class Versions(unittest.TestCase):

    def test_parse_and_compare(self):
        self.assertEqual(upd.parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(upd.parse_version("1.3"), (1, 3))
        self.assertTrue(upd.is_newer("v1.3.1", "1.3.0"))
        self.assertTrue(upd.is_newer("v1.3", "1.2.9"))
        self.assertFalse(upd.is_newer("v1.3.0", "1.3.0"))
        self.assertFalse(upd.is_newer("v1.2.9", "1.3.0"))

    def test_tag_without_digits_is_not_newer(self):
        # Ein Tag wie "dubforge-v2.0.0" liest sich als (0,) - eine
        # bestehende Installation wuerde nie wieder ein Update sehen.
        self.assertEqual(upd.parse_version("dubforge-v2.0.0"), (0,))
        self.assertFalse(upd.is_newer("dubforge-v2.0.0", "1.0.0"))

    def test_only_this_repository_is_trusted(self):
        self.assertTrue(upd._trusted(
            "https://api.github.com/repos/%s/releases/latest" % upd.REPO))
        self.assertTrue(upd._trusted(
            "https://api.github.com/repos/%s/zipball/v1.0.0" % upd.REPO))
        self.assertFalse(upd._trusted(
            "https://api.github.com/repos/someone/else/zipball/v1.0.0"))
        self.assertFalse(upd._trusted("http://github.com/%s" % upd.REPO))
        self.assertFalse(upd._trusted("https://example.com/evil.zip"))


class SwapScript(unittest.TestCase):
    """Der Text des Tauschskripts / the text of the swap script."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="updtext_")
        self.app = os.path.join(self.d, "app")
        os.makedirs(self.app)
        io.open(os.path.join(self.app, "DubForge.pyw"), "w").write("x")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def text(self):
        return upd.swap_text(os.path.join(self.d, "staged"), self.app,
                             os.path.join(self.d, "bak"),
                             os.path.join(self.d, "log.txt"),
                             "DubForge", "v9.9.9", 4242,
                             dump=os.path.join(self.d, "task.txt"))

    def test_no_pipe_in_the_wait_loop(self):
        # Der Fehler, der das Update stehen liess: in einem Prozess ohne
        # Konsole kehrt "tasklist | find" nie zurueck.
        # Nur die Befehle zaehlen, nicht die rem-Zeilen daneben.
        cmds = "; ".join(l for l in self.text().splitlines()
                         if not l.strip().lower().startswith("rem"))
        self.assertNotIn("|", cmds, "a pipe is back in the swap script")
        self.assertIn("findstr", cmds)
        self.assertIn("4242", cmds)

    def test_nothing_is_left_unfilled(self):
        t = self.text()
        for slot in ("__SRC__", "__DST__", "__BAK__", "__LOG__", "__DUMP__",
                     "__TAG__", "__PID__", "__RESTART__"):
            self.assertNotIn(slot, t, slot)

    def test_restart_avoids_the_console(self):
        # Ueber "Start DubForge.bat" ginge ein Konsolenfenster auf.
        io.open(os.path.join(self.app, "Start DubForge.bat"), "w").write("x")
        cmd = upd._restart_command(self.app, "DubForge")
        self.assertIn("DubForge.pyw", cmd)
        self.assertNotIn(".bat", cmd)

    def test_restart_falls_back_to_the_starter(self):
        os.remove(os.path.join(self.app, "DubForge.pyw"))
        io.open(os.path.join(self.app, "Start DubForge.bat"), "w").write("x")
        self.assertIn(".bat", upd._restart_command(self.app, "DubForge"))


@unittest.skipUnless(IS_WINDOWS, "the swap is Windows only")
class SwapRuns(unittest.TestCase):
    """Der Tausch wird wirklich ausgefuehrt / the swap really runs."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="updrun_")
        self.app = os.path.join(self.d, "app")
        self.staged = os.path.join(self.d, "staged")
        os.makedirs(self.app)
        os.makedirs(self.staged)
        io.open(os.path.join(self.app, "DubForge.pyw"), "w").write("alt\n")
        io.open(os.path.join(self.staged, "DubForge.pyw"), "w").write("neu\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_swap_waits_copies_and_ends(self):
        # Eine kurzlebige "App": das Skript muss ihr Ende bemerken.
        stand_in = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(2.5)"])
        dump = os.path.join(self.d, "task.txt")
        log = os.path.join(self.d, "log.txt")
        text = upd.swap_text(self.staged, self.app, os.path.join(self.d, "bak"),
                             log, "GhostApp", "v9.9.9", stand_in.pid, dump=dump)
        bat = os.path.join(self.d, "swap.bat")
        io.open(bat, "w", encoding="cp1252", errors="replace",
                newline="\r\n").write(text)

        flags = 0x08000000 | 0x00000200        # wie in apply() / as in apply()
        swap = subprocess.Popen([os.environ.get("COMSPEC", "cmd.exe"), "/c", bat],
                                cwd=self.d, close_fds=True, creationflags=flags)
        stand_in.wait()

        end = time.time() + 40
        while time.time() < end and swap.poll() is None:
            time.sleep(0.2)
        if swap.poll() is None:
            swap.kill()
            self.fail("the swap script hung instead of finishing")

        written = io.open(os.path.join(self.app, "DubForge.pyw")).read()
        self.assertEqual(written.strip(), "neu", "the update was not applied")
        text_log = io.open(log, encoding="cp1252", errors="replace").read()
        self.assertNotIn("Update abgebrochen", text_log, text_log)
        self.assertFalse(os.path.exists(dump), "the tasklist dump was left behind")

    def test_apply_starts_the_swap_without_a_window(self):
        # apply() darf nicht abgekoppelt starten - dann bleibt es haengen.
        seen = {}

        def fake_popen(cmd, **kw):
            seen["flags"] = kw.get("creationflags")

            class P(object):
                pid = 0
            return P()

        real = upd.subprocess.Popen
        upd.subprocess.Popen = fake_popen
        try:
            upd.apply(self.staged, self.app, which="GhostApp", tag="v9.9.9")
        finally:
            upd.subprocess.Popen = real
        self.assertTrue(seen["flags"] & 0x08000000, "CREATE_NO_WINDOW missing")
        self.assertFalse(seen["flags"] & 0x00000008, "still DETACHED_PROCESS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
