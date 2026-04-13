from dataclasses import dataclass, field
import flet as ft

@ft.observable
@dataclass
class AppModel:
    route: str = "/"
    library: list[str] = field(default_factory=list)
    selected_book: str | None = None
    # Default to Light to match your 'Tweakon' Graphite reference start
    theme_mode: ft.ThemeMode = ft.ThemeMode.LIGHT

    def navigate(self, new_route: str):
        """Standard navigation handler."""
        self.route = new_route
        if ft.context.page:
            ft.context.page.route = new_route
            ft.context.page.update()

    def route_change(self, e: ft.RouteChangeEvent):
        """Syncs the model when the browser/system route changes."""
        self.route = e.route

    def view_popped(self, e: ft.ViewPopEvent):
        """Handles back-button logic."""
        self.navigate("/")

    def toggle_theme(self):
        """Switches between slick light and graphite dark modes."""
        self.theme_mode = (
            ft.ThemeMode.DARK 
            if self.theme_mode == ft.ThemeMode.LIGHT 
            else ft.ThemeMode.LIGHT
        )

    def import_book(self, path: str):
        """Adds a new book path (PDF or EPUB) to the library."""
        if path and path not in self.library:
            self.library = [*self.library, path]

    def open_book(self, path: str):
        """Selects a book and moves to the reader view."""
        self.selected_book = path
        self.navigate("/reader")