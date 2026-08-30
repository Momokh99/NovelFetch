---
description: Scaffold a new KivyMD screen with proper structure and patterns.
agent: build
---

Create a new KivyMD screen for the NovelFetch app. Follow these patterns:

## Screen Structure

1. Create Python file in `android_app/screens/` with:
   - Proper imports from kivymd.uix
   - Screen class inheriting from MDScreen
   - __init__ method with proper setup
   - Helper methods for common operations
   - Proper async integration if needed

2. Create KV file in `android_app/kv/` with:
   - Proper theme imports
   - Screen layout with TopBar
   - Proper padding and spacing using theme constants
   - Adaptive layouts where appropriate

3. Update `android_app/novelfetch.kv` to include new KV file

4. Update `android_app/screens/__init__.py` to export new screen

## Template

```python
# android_app/screens/{screen_name}.py
from kivymd.uix.screen import MDScreen
from screens import theme

class {ScreenName}Screen(MDScreen):
    """Screen for {purpose}."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initialized = False
    
    def on_enter(self):
        """Called when screen becomes visible."""
        if not self._initialized:
            self._setup()
            self._initialized = True
    
    def _setup(self):
        """One-time setup for the screen."""
        pass
    
    def on_leave(self):
        """Called when screen is hidden."""
        pass
```

```kv
# android_app/kv/{screen_name}.kv
#:import theme screens.theme

<{ScreenName}Screen>:
    MDBoxLayout:
        orientation: "vertical"
        
        TopBar:
            title: "{Screen Title}"
            back: True
        
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                adaptive_height: True
                padding: (theme.PAGE_PAD, theme.PAGE_PAD)
                spacing: theme.SECTION_GAP
                
                # Add your content here
```

## Requirements

- Use KivyMD 2.0 patterns (MDListItem, not OneLineListItem)
- Follow theme system from screens/theme.py
- Use adaptive_height where appropriate
- Proper async integration if network calls needed
- Add tests in tests/ directory

Screen name: $ARGUMENTS
