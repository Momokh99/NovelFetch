# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Textual TUI binary (novelfetch-tui).
# Build:  pyinstaller packaging/novelfetch-tui.spec
# Output: dist/novelfetch-tui(.exe)

import os

repo_root = os.path.dirname(SPECPATH)

a = Analysis(
    [os.path.join(repo_root, "tui", "main.py")],
    pathex=[repo_root],
    binaries=[],
    datas=[(os.path.join(repo_root, "tui", "novelfetch.tcss"), ".")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["gi", "pygobject", "kivy", "kivymd"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="novelfetch-tui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
)
