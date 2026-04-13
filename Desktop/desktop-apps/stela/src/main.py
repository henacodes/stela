import flet as ft
from components.app import App

def main(page: ft.Page):
    # Minimal Shadcn-ish Theme Config
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(primary="#18181b", surface="#ffffff")
    )
    # Using render_views for the reactive Gallery-style flow
    page.render_views(lambda: App())

if __name__ == "__main__":
    ft.run(main)