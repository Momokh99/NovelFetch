---
name: kivymd-development
description: KivyMD 2.0 development patterns for Python mobile apps. Use when working with Kivy, KivyMD, KV language, Android UI, or mobile Python development. Covers KivyMD 2.0 migration, KV patterns, async integration, testing, and performance optimization.
---

# KivyMD Development Skill

Expert guidance for KivyMD 2.0 mobile app development with Python, covering architecture patterns, KV language, testing, and Android-specific considerations.

## KivyMD 2.0 Migration

### Widget Import Changes

KivyMD 2.0 renamed many widgets. Use these mappings:

```python
# OLD (KivyMD 1.x)                    # NEW (KivyMD 2.0)
from kivymd.uix.list import (          from kivymd.uix.list import (
    OneLineListItem,                       MDListItem,
    TwoLineListItem,                       MDListItemHeadlineText,
    ThreeLineListItem,                     MDListItemSupportingText,
    OneLineAvatarListItem,                 MDListItemLeadingAvatar,
    TwoLineAvatarListItem,                 MDListItemTrailingIcon,
    OneLineIconListItem,                   MDListItemLeadingIcon,
    IconLeftWidget,                        # Use MDListItemLeadingIcon
    IconRightWidget,                       # Use MDListItemTrailingIcon
    OneLineAvatarIconListItem,             # Compose with leading/trailing
)

from kivymd.uix.dialog import (        from kivymd.uix.dialog import (
    MDDialog,                              MDDialog,
    DialogContent,                         MDDialogContentContainer,
    DialogHeadlineText,                    MDDialogHeadlineText,
    DialogSupportingText,                  MDDialogSupportingText,
    DialogButtonContainer,                 MDDialogButtonContainer,
    DialogActionButton,                    MDDialogButtonContainer
)

from kivymd.uix.button import (        from kivymd.uix.button import (
    MDRaisedButton,                        MDRaisedButton,
    MDFlatButton,                          MDFlatButton,
    MDIconButton,                          MDIconButton,
)
```

### KV Language Patterns

```kv
# KivyMD 2.0 KV patterns
<SmartTileWithBody>:
    # Use MDListItem composition instead of deprecated widgets
    MDListItem:
        MDListItemLeadingIcon:
            icon: "book"
        MDListItemHeadlineText:
            text: root.title
        MDListItemSupportingText:
            text: root.subtitle

# Proper theming in KV
<CustomCard>:
    theme_bg_color: "Custom"
    bg_color: app.theme_cls.primaryColor if not root.elevated else app.theme_cls.surfaceColor

# Adaptive sizing
<ResponsiveGrid>:
    cols: max(2, root.width // dp(200))  # Responsive columns
    adaptive_height: True
```

## Architecture Patterns

### Screen Management

```python
# screens/__init__.py - Centralized screen registry
from screens.main_screen import MainScreen
from screens.home_tab import HomeTab
from screens.search_tab import SearchTab
from screens.reader import ReaderScreen

__all__ = [
    "MainScreen",
    "HomeTab",
    "SearchTab",
    "ReaderScreen",
]
```

### App Structure Pattern

```python
# android_app/main.py
class NovelFetchApp(MDApp):
    title = "NovelFetch"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Resource path setup
        from kivy.resources import resource_add_path
        resource_add_path(_APP_DIR)
        self.kv_file = os.path.join(_APP_DIR, "novelfetch.kv")
    
    def build(self):
        # Platform-specific setup
        if platform == "android":
            os.chdir(self.user_data_dir)
        else:
            os.chdir(_ROOT)
        
        # Theme initialization
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        
        # Async loop start
        from async_runner import async_loop
        async_loop.start()
        
        # Register custom widgets
        import screens.browse
        import screens.topbar
        from screens import MainScreen
        return MainScreen()
```

### Async Integration Pattern

```python
# async_runner.py - Bridge asyncio to Kivy Clock
import asyncio
from kivy.clock import Clock

class AsyncLoop:
    def __init__(self):
        self._loop = None
        self._task = None
    
    def start(self):
        self._loop = asyncio.new_event_loop()
        self._task = Clock.schedule_interval(self._run_once, 0)
    
    def _run_once(self, dt):
        if self._loop and self._loop.is_running():
            self._loop.call_soon(self._loop.stop)
            self._loop.run_forever()
    
    def stop(self):
        if self._task:
            self._task.cancel()
        if self._loop:
            self._loop.close()
    
    async def run(self, coro):
        return await asyncio.ensure_future(coro, loop=self._loop)

async_loop = AsyncLoop()
```

## Testing Patterns

### Unit Testing Pure Logic

```python
# tests/test_reader_logic.py
import pytest
from screens.reader import _strip_control_chars, _greedy_wrap

def test_strip_control_chars_removes_rtl_marks():
    text = "مرحبا\u200f بالعالم"
    clean = _strip_control_chars(text)
    assert "\u200f" not in clean
    assert clean == "مرحبا بالعالم"

def test_font_clamping():
    def clamp_font(size, delta):
        return min(28, max(14, size + delta))
    
    assert clamp_font(16, 2) == 18
    assert clamp_font(16, -10) == 14
    assert clamp_font(28, 2) == 28
```

### UI Logic Testing

```python
# tests/test_search_tab_logic.py
import pytest
from screens.search_tab import SearchTab

def test_search_debounce():
    # Test search debouncing logic
    tab = SearchTab()
    tab._search_text = "test"
    tab._last_search = 0
    
    # Simulate rapid typing
    tab._on_search_text(None, "t")
    tab._on_search_text(None, "te")
    tab._on_search_text(None, "tes")
    tab._on_search_text(None, "test")
    
    # Only last search should execute
    assert tab._search_text == "test"
```

### Mocking Kivy Components

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_app():
    with patch('kivymd.app.MDApp.get_running_app') as mock:
        app = MagicMock()
        app.theme_cls.theme_style = "Dark"
        mock.return_value = app
        yield app

@pytest.fixture
def mock_clock():
    with patch('kivy.clock.Clock') as mock:
        yield mock
```

## Performance Optimization

### Chunked Rendering for Large Text

```python
# android_app/screens/reader.py
_MAX_CHUNK_PX = 2500  # Max pixels per Kivy Label (GPU texture limit)

def lines_per_chunk(line_h, cap=_MAX_CHUNK_PX):
    """Calculate lines per chunk to stay under GPU texture limit."""
    return max(1, int(cap // line_h))

def pack_lines_into_chunks(lines, per_chunk):
    """Split text lines into chunks for rendering."""
    chunks = []
    for i in range(0, len(lines), per_chunk):
        chunk_lines = lines[i:i + per_chunk]
        chunks.append("\n".join(chunk_lines))
    return chunks

# Usage in screen
def _render_chunks(self):
    chunks = pack_lines_into_chunks(self._lines, self._per_chunk)
    for chunk in chunks:
        label = MDLabel(
            text=chunk,
            adaptive_height=True,
            font_size=self._font_size,
        )
        self.ids.body_box.add_widget(label)
```

### Lazy Loading for Lists

```python
# Lazy row loading for large chapter lists
def _load_more_chapters(self, *args):
    if self._loading or self._all_loaded:
        return
    
    self._loading = True
    start = len(self._chapters)
    end = start + 40  # Load 40 at a time
    
    new_chapters = self._source.get_chapters(
        self._novel_url, start=start, end=end
    )
    
    if not new_chapters:
        self._all_loaded = True
    else:
        self._chapters.extend(new_chapters)
        self._update_display()
    
    self._loading = False
```

### Image Caching

```python
# android_app/screens/utils.py
import os
import hashlib
from kivy.network.urlrequest import UrlRequest

_cover_cache = {}

def load_cover(url, callback):
    """Load cover image with caching."""
    if url in _cover_cache:
        callback(_cover_cache[url])
        return
    
    # Generate cache key
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_path = os.path.join("novels", ".covers", f"{cache_key}.png")
    
    if os.path.exists(cache_path):
        _cover_cache[url] = cache_path
        callback(cache_path)
        return
    
    def on_success(req, result):
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'wb') as f:
            f.write(result)
        _cover_cache[url] = cache_path
        callback(cache_path)
    
    UrlRequest(url, on_success=on_success)
```

## Android-Specific Considerations

### Platform Detection

```python
from kivy.utils import platform

if platform == "android":
    # Android-specific code
    from android import wakelock
    wakelock.acquire("my_app")
elif platform == "ios":
    # iOS-specific code
    pass
else:
    # Desktop fallback
    pass
```

### Storage Paths

```python
from kivy.app import App

app = App.get_running_app()
# User data directory (persists across app restarts)
user_data = app.user_data_dir
# Cache directory (can be cleared)
cache_data = app.cache_dir
```

### Permission Handling

```python
# Android permissions (if needed)
if platform == "android":
    from android.permissions import request_permissions, Permission
    
    request_permissions([
        Permission.READ_EXTERNAL_STORAGE,
        Permission.WRITE_EXTERNAL_STORAGE,
    ])
```

## Common Pitfalls & Solutions

### 1. KV File Not Loading

**Problem:** KV file not found or widgets not created.

**Solution:** Ensure resource path is set correctly:
```python
from kivy.resources import resource_add_path
resource_add_path(os.path.dirname(__file__))
```

### 2. Async Not Working

**Problem:** Async functions not executing.

**Solution:** Use Clock.schedule_interval to pump the event loop:
```python
Clock.schedule_interval(lambda dt: asyncio.ensure_future(your_coro()), 0)
```

### 3. Widget Not Updating

**Problem:** UI not reflecting data changes.

**Solution:** Trigger update manually:
```python
# Force widget refresh
widget.canvas.ask_update()

# Or use Clock for delayed update
Clock.schedule_once(lambda dt: widget.canvas.ask_update(), 0)
```

### 4. Memory Leaks with Image Caching

**Problem:** Images not being garbage collected.

**Solution:** Use weak references and clear cache:
```python
import weakref

_cover_cache = weakref.WeakValueDictionary()

def clear_cache():
    _cover_cache.clear()
```

### 5. Android Back Button

**Problem:** Back button closes app instead of navigating.

**Solution:** Override on_back_button:
```python
class MainScreen(MDScreen):
    def on_back_button(self):
        if self.current_screen != 'home':
            self.go_back()
            return True  # Handled
        return False  # Let app close
```

## Project-Specific Patterns

### Theme System

This project uses HSL-driven theming:

```python
# android_app/screens/theme.py
from colorsys import hls_to_rgb

def hsl_rgba(h, s, l, a=1.0):
    """HSL (h: 0-360, s/l: 0-100) -> Kivy RGBA list."""
    r, g, b = hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return [round(r, 4), round(g, 4), round(b, 4), a]

ACCENT = hsl_rgba(210, 95, 55)  # Vivid blue accent
```

### Arabic RTL Support

```python
# android_app/screens/reader.py
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _HAS_ARABIC_SHAPING = True
except ImportError:
    _HAS_ARABIC_SHAPING = False

def _shape_arabic_text(text):
    if not _HAS_ARABIC_SHAPING:
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped, base_dir="R")
```

## References

- KivyMD 2.0 Documentation: https://kivymd.readthedocs.io/
- Kivy Documentation: https://kivy.org/doc/stable/
- KivyMD GitHub: https://github.com/kivymd/KivyMD
- Kivy Garden: https://garden.kivy.org/
