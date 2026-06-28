"""Tests for the light/dark theme toggle feature.

These are structural/content tests that verify the frontend files contain the
required elements and CSS for the theme toggle.  They run fast without a browser
and are deterministic.
"""

from pathlib import Path

# Resolve frontend directory relative to this file
FRONTEND = Path(__file__).parent.parent.parent / "frontend"


def _html() -> str:
    return (FRONTEND / "index.html").read_text()


def _css() -> str:
    return (FRONTEND / "style.css").read_text()


def _js() -> str:
    return (FRONTEND / "script.js").read_text()


# ---------------------------------------------------------------------------
# HTML: toggle button must be present with accessibility attributes
# ---------------------------------------------------------------------------

class TestThemeToggleHTML:
    def test_toggle_button_exists(self):
        """A button element with id='themeToggle' must exist."""
        assert 'id="themeToggle"' in _html(), (
            "index.html must contain a button with id='themeToggle'"
        )

    def test_toggle_button_aria_label(self):
        """The toggle button must have an aria-label for accessibility."""
        html = _html()
        assert "aria-label" in html, (
            "themeToggle button must have an aria-label attribute"
        )

    def test_toggle_button_has_sun_or_moon_icon(self):
        """Button must contain inline SVG or a Unicode/emoji sun/moon icon."""
        html = _html()
        has_svg = "<svg" in html and "themeToggle" in html
        has_emoji = any(icon in html for icon in ["☀", "🌙", "☽", "☾"])
        assert has_svg or has_emoji, (
            "themeToggle button must include a sun/moon SVG or character"
        )


# ---------------------------------------------------------------------------
# CSS: light theme variables must exist and transitions must be declared
# ---------------------------------------------------------------------------

class TestThemeToggleCSS:
    def test_light_theme_variables_defined(self):
        """A [data-theme='light'] or .light-theme selector must define CSS vars."""
        css = _css()
        has_data_attr = "[data-theme=" in css or '[data-theme="light"]' in css
        has_class = ".light-theme" in css or ".light" in css
        assert has_data_attr or has_class, (
            "style.css must define a light-theme selector with CSS variables"
        )

    def test_transition_on_body_or_root(self):
        """Body or :root must have a 'transition' property for smooth toggling."""
        css = _css()
        assert "transition" in css, (
            "style.css must include a transition property for smooth theme switching"
        )

    def test_theme_toggle_button_styles(self):
        """There must be CSS rules targeting #themeToggle."""
        assert "#themeToggle" in _css(), (
            "style.css must contain styles for #themeToggle"
        )


# ---------------------------------------------------------------------------
# JS: toggle function and persistence via localStorage must be present
# ---------------------------------------------------------------------------

class TestThemeToggleJS:
    def test_toggle_function_or_listener(self):
        """script.js must reference themeToggle and handle click/toggle."""
        js = _js()
        assert "themeToggle" in js, (
            "script.js must reference the themeToggle element"
        )

    def test_localStorage_persistence(self):
        """Theme preference must be saved to / read from localStorage."""
        js = _js()
        assert "localStorage" in js, (
            "script.js must use localStorage to persist the theme preference"
        )

    def test_data_theme_or_class_toggled(self):
        """JS must set data-theme attribute or toggle a theme class on document."""
        js = _js()
        has_data_attr = "data-theme" in js or "setAttribute" in js
        has_class = "classList" in js and ("dark" in js or "light" in js)
        assert has_data_attr or has_class, (
            "script.js must toggle a data-theme attribute or a theme class"
        )
