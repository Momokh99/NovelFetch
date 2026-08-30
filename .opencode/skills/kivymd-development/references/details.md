# KivyMD Development References

Detailed examples and patterns from the NovelFetch codebase.

## Table of Contents

1. [Screen Navigation](#screen-navigation)
2. [Async Patterns](#async-patterns)
3. [KV Language Examples](#kv-language-examples)
4. [Widget Composition](#widget-composition)
5. [Testing Examples](#testing-examples)

---

## Screen Navigation

### MainScreen with ScreenManager

```python
# android_app/screens/main_screen.py
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager

class MainScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.screen_manager = MDScreenManager()
        self.add_widget(self.screen_manager)
        
        # Register screens
        self.screen_manager.add_widget(HomeTab(name="home"))
        self.screen_manager.add_widget(SearchTab(name="search"))
        self.screen_manager.add_widget(UpdateTab(name="updates"))
        self.screen_manager.add_widget(HistoryTab(name="history"))
        self.screen_manager.add_widget(SettingsTab(name="settings"))
    
    def goto(self, name, **kwargs):
        """Navigate to screen by name."""
        screen = self.screen_manager.get_screen(name)
        if hasattr(screen, 'on_enter'):
            screen.on_enter(**kwargs)
        self.screen_manager.current = name
    
    def back(self):
        """Go back to previous screen."""
        if len(self.screen_manager.screen_history) > 1:
            self.screen_manager.current = self.screen_manager.screen_history[-2]
```

### KV for Navigation Bar

```kv
# android_app/kv/main_screen.kv
<MainScreen>:
    MDBoxLayout:
        orientation: "vertical"
        
        MDScreenManager:
            id: screen_manager
        
        MDBottomNavigation:
            id: nav_bar
            MDBottomNavigationItem:
                name: "home"
                text: "Library"
                icon: "bookshelf"
            MDBottomNavigationItem:
                name: "search"
                text: "Search"
                icon: "magnify"
            MDBottomNavigationItem:
                name: "updates"
                text: "Updates"
                icon: "update"
            MDBottomNavigationItem:
                name: "history"
                text: "History"
                icon: "history"
            MDBottomNavigationItem:
                name: "settings"
                text: "Settings"
                icon: "cog"
```

---

## Async Patterns

### AsyncRunner Bridge

```python
# android_app/async_runner.py
import asyncio
from kivy.clock import Clock

class AsyncLoop:
    """Bridge asyncio event loop to Kivy's Clock thread."""
    
    def __init__(self):
        self._loop = None
        self._task = None
        self._running = False
    
    def start(self):
        """Start the async event loop."""
        if self._running:
            return
        
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._task = Clock.schedule_interval(self._pump, 0)
        self._running = True
    
    def _pump(self, dt):
        """Pump the asyncio event loop."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon(self._loop.stop)
            try:
                self._loop.run_forever()
            except RuntimeError:
                pass
    
    def stop(self):
        """Stop the async event loop."""
        if self._task:
            self._task.cancel()
            self._task = None
        if self._loop:
            self._loop.close()
            self._loop = None
        self._running = False
    
    async def run(self, coro):
        """Run a coroutine in the async loop."""
        if not self._loop:
            raise RuntimeError("AsyncLoop not started")
        return await asyncio.ensure_future(coro, loop=self._loop)
    
    def create_task(self, coro):
        """Create a task without waiting for it."""
        if not self._loop:
            raise RuntimeError("AsyncLoop not started")
        return asyncio.ensure_future(coro, loop=self._loop)

# Singleton instance
async_loop = AsyncLoop()
```

### Using Async in Screens

```python
# android_app/screens/reader.py
class ReaderScreen(MDScreen):
    def _load_chapter(self, url):
        """Load chapter asynchronously."""
        async_loop.create_task(self._fetch_chapter(url))
    
    async def _fetch_chapter(self, url):
        """Fetch chapter content from network."""
        try:
            from httpx import AsyncClient
            async with AsyncClient() as client:
                response = await client.get(url)
                text = response.text
                self._display_text(text)
        except Exception as e:
            self._show_error(str(e))
    
    def _display_text(self, text):
        """Display text in reader (must be called from main thread)."""
        Clock.schedule_once(lambda dt: self._update_display(text), 0)
    
    def _update_display(self, text):
        """Update display widgets."""
        self.ids.body_box.clear_widgets()
        lines = text.split('\n')
        chunks = pack_lines_into_chunks(lines, self._per_chunk)
        for chunk in chunks:
            label = MDLabel(text=chunk, adaptive_height=True)
            self.ids.body_box.add_widget(label)
```

---

## KV Language Examples

### Complex Layouts

```kv
# android_app/kv/reader.kv
#:import theme screens.theme

<ReaderScreen>:
    MDBoxLayout:
        orientation: "vertical"
        
        TopBar:
            id: header
            back: True
        
        ScrollView:
            id: scroll
            
            MDBoxLayout:
                id: body_box
                orientation: "vertical"
                adaptive_height: True
                padding: (theme.PAGE_PAD, theme.PAGE_PAD)
                spacing: "0dp"
        
        MDBoxLayout:
            id: bottom_divider
            size_hint_y: None
            height: "1dp"
        
        MDBoxLayout:
            id: bottom_bar
            orientation: "horizontal"
            size_hint_y: None
            height: "56dp"
            padding: "8dp"
            spacing: "4dp"
            
            MDIconButton:
                id: prev_btn
                icon: "skip-previous"
            
            MDIconButton:
                id: font_down_btn
                icon: "format-font-size-decrease"
            
            MDLabel:
                id: font_size_label
                text: "16"
                halign: "center"
                valign: "middle"
                theme_text_color: "Secondary"
                font_style: "Label"
                role: "medium"
            
            MDIconButton:
                id: font_up_btn
                icon: "format-font-size-increase"
            
            MDIconButton:
                id: translate_btn
                icon: "translate"
            
            MDLabel:
                id: counter
                text: ""
                halign: "center"
                valign: "middle"
                bold: True
                font_style: "Label"
                role: "medium"
                theme_text_color: "Secondary"
            
            MDIconButton:
                id: next_btn
                icon: "skip-next"
```

### Dynamic Theming

```kv
# Dynamic theme colors in KV
<CustomCard>:
    theme_bg_color: "Custom"
    bg_color: (
        app.theme_cls.primaryColor if root.is_selected 
        else app.theme_cls.surfaceColor
    )
    
    MDLabel:
        text: root.title
        theme_text_color: "Primary" if root.is_selected else "Secondary"
```

### Adaptive Grid Layout

```kv
# Responsive grid that adapts to screen size
<NovelGrid>:
    cols: max(2, int(root.width / dp(200)))
    spacing: dp(8)
    padding: dp(8)
    adaptive_height: True
    
    # Grid items will be added dynamically
```

---

## Widget Composition

### Custom Card Widget

```python
# android_app/screens/home_tab.py
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

class NovelCard(MDCard):
    """Custom card for novel display."""
    
    def __init__(self, novel_data, **kwargs):
        super().__init__(**kwargs)
        self.novel_data = novel_data
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(200)
        self.padding = dp(8)
        self.spacing = dp(8)
        self.radius = [14, 14, 14, 14]
        
        # Add cover image
        cover = Image(
            source=novel_data.get('cover', ''),
            allow_stretch=True,
            keep_ratio=True,
        )
        self.add_widget(cover)
        
        # Add title
        title = MDLabel(
            text=novel_data.get('title', ''),
            font_style="Title",
            role="medium",
            adaptive_height=True,
        )
        self.add_widget(title)
```

### Custom List Item

```python
# android_app/screens/chapter_list.py
from kivymd.uix.list import MDListItem, MDListItemHeadlineText, MDListItemSupportingText

class ChapterListItem(MDListItem):
    """Custom list item for chapters."""
    
    def __init__(self, chapter_data, **kwargs):
        super().__init__(**kwargs)
        self.chapter_data = chapter_data
        
        # Add leading number
        num_label = MDListItemLeadingIcon(
            icon="book-open-page-variant",
        )
        self.add_widget(num_label)
        
        # Add headline
        headline = MDListItemHeadlineText(
            text=chapter_data.get('title', ''),
        )
        self.add_widget(headline)
        
        # Add supporting text
        supporting = MDListItemSupportingText(
            text=f"Chapter {chapter_data.get('number', '')}",
        )
        self.add_widget(supporting)
```

---

## Testing Examples

### Pure Logic Tests

```python
# tests/test_reader_logic.py
import pytest
from screens.reader import (
    _strip_control_chars,
    _CTRL_CHARS_RE,
    _greedy_wrap,
    _wrap_rtl_lines,
    lines_per_chunk,
    pack_lines_into_chunks,
)

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
    assert clamp_font(14, -2) == 14

def test_greedy_wrap_basic():
    widths = [100, 100, 100, 100]
    space_w = 10
    avail = 250
    
    lines = _greedy_wrap(widths, space_w, avail)
    
    # Should wrap at 2 words per line (100 + 10 + 100 = 210 < 250)
    assert len(lines) == 2
    assert lines[0] == [0, 1]
    assert lines[1] == [2, 3]

def test_pack_lines_into_chunks():
    lines = ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5"]
    chunks = pack_lines_into_chunks(lines, 2)
    
    assert len(chunks) == 3
    assert chunks[0] == "Line 1\nLine 2"
    assert chunks[1] == "Line 3\nLine 4"
    assert chunks[2] == "Line 5"
```

### UI Logic Tests

```python
# tests/test_search_tab_logic.py
import pytest
from screens.search_tab import SearchTab

def test_search_initial_state():
    tab = SearchTab()
    assert tab._search_text == ""
    assert tab._results == []
    assert tab._loading == False

def test_search_pagination():
    tab = SearchTab()
    tab._page = 1
    tab._has_more = True
    
    # Simulate loading more results
    tab._load_more()
    
    assert tab._page == 2

def test_search_clear():
    tab = SearchTab()
    tab._search_text = "test query"
    tab._results = [{"title": "Test"}]
    
    tab._clear_search()
    
    assert tab._search_text == ""
    assert tab._results == []
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
        app.theme_cls.primary_palette = "Blue"
        mock.return_value = app
        yield app

@pytest.fixture
def mock_clock():
    with patch('kivy.clock.Clock') as mock:
        mock.schedule_once = MagicMock()
        mock.schedule_interval = MagicMock()
        yield mock

@pytest.fixture
def mock_async_loop():
    with patch('async_runner.async_loop') as mock:
        mock.create_task = MagicMock()
        mock.run = MagicMock()
        yield mock
```

---

## Performance Tips

1. **Use adaptive_height=True** for dynamic content
2. **Chunk large text** to stay under GPU texture limits (2500px)
3. **Cache images** to avoid repeated downloads
4. **Use Clock.schedule_once** for deferred UI updates
5. **Minimize widget creation** in loops - reuse when possible
6. **Use WeakValueDictionary** for caches to prevent memory leaks

---

## Common KivyMD 2.0 Patterns

```python
# Dialog with proper KivyMD 2.0 structure
def show_dialog(self, title, message, on_confirm):
    dialog = MDDialog(
        MDDialogHeadlineText(text=title),
        MDDialogSupportingText(text=message),
        MDDialogButtonContainer(
            MDFlatButton(
                text="Cancel",
                on_release=lambda x: dialog.dismiss(),
            ),
            MDRaisedButton(
                text="Confirm",
                on_release=lambda x: (on_confirm(), dialog.dismiss()),
            ),
            spacing="12dp",
            padding=("12dp", "0dp", "12dp", "0dp"),
        ),
    )
    dialog.open()
```
