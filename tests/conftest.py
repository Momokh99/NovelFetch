"""Test bootstrap: expose repo-root packages (core, sources, tui, gui).

Tests import both the shared packages (core, sources) and the Kivy GUI
(gui.screens.*). Adding the repo root to sys.path makes every top-level
package importable; there is no longer any bare `screens` name collision.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
