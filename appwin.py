# -*- coding: utf-8 -*-
"""
appwin.py - Fenstersymbol und Taskleisten-Identitaet.
appwin.py - window icon and taskbar identity.

Ohne eigene Kennung zeigt Windows fuer jedes Fenster das Symbol von
pythonw.exe und gruppiert DubForge und DubStage unter "Python". Mit
Kennung und Symbol erscheinen beide als eigene Apps - und passen zu den
Verknuepfungen, die das Setup anlegt (gleiche AppUserModelID).
"""

import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(APP_DIR, "assets")

# Muss mit AppUserModelID in installer/DubStage.iss uebereinstimmen.
APP_IDS = {
    "DubForge": "xmrius.DubStage.DubForge",
    "DubStage": "xmrius.DubStage.DubStage",
}


def set_app_id(which):
    """Vor dem ersten Fenster aufrufen - danach wirkt es nicht mehr sicher."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            APP_IDS.get(which, "xmrius.DubStage." + which))
    except Exception:
        pass


def set_dpi_aware():
    """Vor dem ersten Fenster: in echten Pixeln zeichnen statt von Windows
    hochgezogen (und dabei unscharf) zu werden. Wer das ruft, muss seine
    Pixelmasse selbst skalieren - DubForge tut es mit px().
    Before the first window: draw in real pixels instead of being stretched
    (and blurred) by Windows. The caller has to scale its own pixel sizes."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        try:
            # systemweit, nicht je Monitor: Tk 8.6 folgt keinem Monitorwechsel
            # system-wide, not per monitor: Tk 8.6 does not follow monitor moves
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
        return True
    except Exception:
        return False


def set_icon(root, which):
    """Symbol fuer das Hauptfenster und alle Dialoge danach."""
    stem = os.path.join(ASSETS, which.lower())
    try:
        if os.name == "nt" and os.path.isfile(stem + ".ico"):
            root.iconbitmap(default=stem + ".ico")
        elif os.path.isfile(stem + ".png"):
            import tkinter as tk
            root._appwin_icon = tk.PhotoImage(file=stem + ".png")
            root.iconphoto(True, root._appwin_icon)
    except Exception:
        pass                      # reine Optik - darf den Start nie stoppen
