from collections.abc import Callable
from dataclasses import dataclass
import flet as ft

# Slick Graphite Palette constants
SLATE_900 = "#0f172a"  # Dark background
SLATE_50   = "#f8fafc"  # Light background
GRAPHITE   = "#18181b"  

@dataclass(frozen=True)
class ThemeContextValue:
    mode: ft.ThemeMode
    seed_color: str  # Changed to str to support hex codes
    toggle_mode: Callable[[], None]
    set_seed_color: Callable[[str], None]

ThemeContext = ft.create_context(
    ThemeContextValue(
        mode=ft.ThemeMode.LIGHT,
        seed_color=GRAPHITE, 
        toggle_mode=lambda: None,
        set_seed_color=lambda color: None,
    )
)