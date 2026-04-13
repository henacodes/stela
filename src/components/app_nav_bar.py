import flet as ft
from typing import Any, cast


@ft.component
def AppNavBar(route: str, on_navigate):
    def nav_item(label: str, icon: ft.IconData, target_route: str):
        selected = route == target_route
        return ft.TextButton(
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
                controls=cast(list[ft.Control], [
                    ft.Icon(icon, color=ft.Colors.PRIMARY if selected else ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(
                        value=label,
                        size=11,
                        color=ft.Colors.PRIMARY if selected else ft.Colors.ON_SURFACE_VARIANT,
                        weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
                    ),
                ]),
            ),
            on_click=lambda _: on_navigate(target_route),
        )

    return cast(Any, ft.Container)(
        border=ft.border.only(top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        content=cast(Any, ft.Row)(
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            controls=cast(list[ft.Control], [
                nav_item("Library", ft.Icons.HOME_OUTLINED, "/"),
                nav_item("Settings", ft.Icons.SETTINGS_OUTLINED, "/settings"),
            ]),
        ),
    )
