import flet as ft
from contexts.app_context import AppContext
from contexts.theme import ThemeContext, ThemeContextValue
from models.app_model import AppModel
from views.library import LibraryView
from views.reader import ReaderView

# Your "Slicky" Graphite Palette
GRAPHITE = "#18181b"

@ft.component
def App() -> ft.View:
    # 1. Initialize Global App State
    app, _ = ft.use_state(AppModel(route=ft.context.page.route))
    seed_color, set_seed_color = ft.use_state(GRAPHITE)

    # 2. Synchronize Route Events
    ft.context.page.on_route_change = app.route_change
    ft.context.page.on_view_pop = app.view_popped

    # 3. Stable Theme Callbacks (Memoized logic)
    toggle_theme = ft.use_callback(
        lambda: app.toggle_theme(), dependencies=[app.theme_mode]
    )

    # 4. Prepare Context Values
    theme_value = ft.use_memo(
        lambda: ThemeContextValue(
            mode=app.theme_mode,
            seed_color=seed_color,      
            toggle_mode=toggle_theme,
            set_seed_color=set_seed_color, 
        ),
        dependencies=[app.theme_mode, toggle_theme, set_seed_color, seed_color],
    )

    # 5. Side Effect: Update Physical Page Theme
    def apply_theme_to_page():
        ft.context.page.theme_mode = app.theme_mode
        ft.context.page.theme = ft.Theme(
            color_scheme_seed=GRAPHITE,
            visual_density=ft.VisualDensity.COMFORTABLE,
        )
        ft.context.page.update()

    ft.on_updated(apply_theme_to_page, [app.theme_mode])

    # 6. Nested Context Provider Tree
    return AppContext(
        app,
        lambda: ThemeContext(
            theme_value,
            lambda: ft.View(
                route="/",
                padding=30,
                # Use a dynamic background color for that slick look
                bgcolor=ft.Colors.SURFACE if app.theme_mode == ft.ThemeMode.LIGHT else "#09090b",
                controls=[
                    LibraryView() if app.route == "/" else ReaderView()
                ],
            ),
        ),
    )