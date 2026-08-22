"""Test bootstrap: expose repo-root shared modules and the Kivy app package.

Import order matters: android_app must precede the repo root so the bare name
``screens`` resolves to android_app/screens (Kivy) and NOT the legacy Textual
TUI screens/ at the root.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "android_app")

for _p in (ROOT, APP):
    if _p not in sys.path:
        sys.path.insert(0, _p)
