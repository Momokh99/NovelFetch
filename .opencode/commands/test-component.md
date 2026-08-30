---
description: Create tests for KivyMD components following project patterns.
agent: build
---

Create comprehensive tests for the specified KivyMD component. Follow these patterns:

## Test Structure

1. Create test file in `tests/` with:
   - Proper pytest imports
   - Unit tests for pure logic
   - UI logic tests with mocked Kivy components
   - Edge cases and error handling

2. Test categories:
   - **Pure Logic**: Test functions without Kivy dependencies
   - **UI Logic**: Test screen/widget logic with mocked components
   - **Integration**: Test component interactions (if applicable)

## Template

```python
# tests/test_{component_name}.py
"""Tests for {component_name}.py"""

import pytest
from unittest.mock import MagicMock, patch
from screens.{component_name} import {ClassName}


class Test{ClassName}PureLogic:
    """Test pure logic functions without Kivy dependencies."""
    
    def test_example_function(self):
        """Test example function with known inputs/outputs."""
        # Arrange
        input_data = "test"
        
        # Act
        result = example_function(input_data)
        
        # Assert
        assert result == expected_output


class Test{ClassName}UILogic:
    """Test UI logic with mocked Kivy components."""
    
    @pytest.fixture
    def mock_app(self):
        with patch('kivymd.app.MDApp.get_running_app') as mock:
            app = MagicMock()
            app.theme_cls.theme_style = "Dark"
            mock.return_value = app
            yield app
    
    def test_initial_state(self):
        """Test component initial state."""
        component = {ClassName}()
        assert component._initialized == False
        assert component._loading == False
    
    def test_method_example(self, mock_app):
        """Test method with mocked dependencies."""
        component = {ClassName}()
        result = component.some_method("input")
        assert result is not None


class Test{ClassName}EdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_input(self):
        """Test with empty input."""
        result = some_function("")
        assert result is not None
    
    def test_none_input(self):
        """Test with None input."""
        with pytest.raises(ValueError):
            some_function(None)
```

## Testing Patterns

1. **Unit tests**: Test pure functions first
2. **Mock Kivy components**: Use unittest.mock.patch
3. **Test initial state**: Verify component setup
4. **Test user interactions**: Simulate button clicks, text input
5. **Test async operations**: Mock async_runner.async_loop
6. **Test error handling**: Verify graceful error handling

## Component to test: $ARGUMENTS

Follow the existing test patterns in tests/ directory. Focus on:
- Pure logic functions
- UI state management
- User interaction handlers
- Error handling
- Edge cases
