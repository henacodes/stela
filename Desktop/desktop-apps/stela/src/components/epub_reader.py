import flet as ft
from dataclasses import dataclass
from typing import Callable, cast


@dataclass
class EpubRenderableSection:
    title: str
    content: str


@ft.component
def EpubReader(
    sections: list[EpubRenderableSection],
    current_page: int,
    is_vertical: bool,
    font_size: int,
    line_height: float,
    text_align: ft.TextAlign,
    on_visible_section_change: Callable[[int], None],
):
    text_style = ft.TextStyle(size=float(font_size), height=line_height)

    if is_vertical:
        return ft.ListView(
            expand=True,
            spacing=12,
            controls=cast(
                list[ft.Control],
                [
                    ft.Container(
                        key=f"epub-section-{i}",
                        on_click=lambda _, idx=i: on_visible_section_change(idx),
                        padding=16,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if i == current_page else None,
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Text(
                                    section.content,
                                    selectable=True,
                                    style=text_style,
                                    text_align=text_align,
                                ),
                            ],
                        ),
                    )
                    for i, section in enumerate(sections)
                ],
            ),
        )

    current_section = sections[current_page]
    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Container(
                padding=16,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text(
                            current_section.content,
                            selectable=True,
                            style=text_style,
                            text_align=text_align,
                        ),
                    ],
                ),
            )
        ],
    )
