# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the KivyMD GUI binary (novelfetch-gui).
# Build:  pyinstaller packaging/novelfetch-gui.spec
# Output: dist/novelfetch-gui(.exe)

import os

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

repo_root = os.path.dirname(SPECPATH)
kivymd_datas, kivymd_binaries, kivymd_hidden = collect_all("kivymd")
# Kivy is often the system package (Arch) whose submodule scan trips on
# namespace-style __path__; bundle its data + dynamic libs directly instead of
# collect_all. The compiled .so and Python modules come from normal analysis.
kivy_datas = collect_data_files("kivy")
kivy_binaries = collect_dynamic_libs("kivy")
kivy_hidden: list[str] = []

a = Analysis(
    [os.path.join(repo_root, "gui", "main.py")],
    pathex=[repo_root],
    binaries=kivymd_binaries + kivy_binaries,
    datas=[
        (os.path.join(repo_root, "gui"), "gui"),
        (os.path.join(repo_root, "tui", "novelfetch.tcss"), "tui"),
    ]
    + kivymd_datas
    + kivy_datas,
    hiddenimports=[
        "kivy.core.window.window_sdl2",
        "kivy.core.text.text_sdl2",
        "kivy.core.image.img_sdl2",
        "kivy.core.gl.tex_region",
        "kivy._event",
        "kivy._metrics",
    ]
    + kivymd_hidden
    + kivy_hidden
    + collect_submodules("kivymd"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["gi", "pygobject", "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="novelfetch-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)
