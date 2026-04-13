import flet as ft

from contexts.app_context import AppContext
from contexts.theme import ThemeContext


@ft.component
def SettingsView():
    app = ft.use_context(AppContext)
    theme = ft.use_context(ThemeContext)

    def on_toggle_theme(e: ft.Event[ft.Switch]):
        wants_dark = bool(e.control.value)
        is_dark = app.theme_mode == ft.ThemeMode.DARK
        if wants_dark != is_dark:
            app.toggle_theme()

    def seed_button(label: str, color: str):
        return ft.Button(
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Container(width=14, height=14, border_radius=999, bgcolor=color),
                    ft.Text(value=label),
                ],
            ),
            on_click=lambda _: theme.set_seed_color(color),
        )

    return ft.Container(
        expand=True,
        padding=24,
        content=ft.Column(
            spacing=18,
            controls=[
                ft.Text(value="Settings", size=28, weight=ft.FontWeight.BOLD),
                ft.Container(
                    padding=16,
                    border_radius=12,
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Text(value="Appearance", weight=ft.FontWeight.BOLD),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(value="Dark mode"),
                                    ft.Switch(
                                        value=app.theme_mode == ft.ThemeMode.DARK,
                                        on_change=on_toggle_theme,
                                    ),
                                ],
                            ),
                            ft.Text(value="Accent color", color=ft.Colors.ON_SURFACE_VARIANT, size=12),
                            ft.Row(
                                spacing=8,
                                wrap=True,
                                controls=[
                                    seed_button("Graphite", "#18181b"),
                                    seed_button("Blue", "#2563eb"),
                                    seed_button("Emerald", "#059669"),
                                    seed_button("Violet", "#7c3aed"),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )
