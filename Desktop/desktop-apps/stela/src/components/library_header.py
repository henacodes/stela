import flet as ft


@ft.component
def LibraryHeader(on_import_files_click, on_import_folder_click):
    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Column(
                spacing=2,
                controls=[
                    ft.Text("My Stela", size=32, weight=ft.FontWeight.BOLD),
                    ft.Text("Your indexed library", color=ft.Colors.ON_SURFACE_VARIANT),
                ],
            ),
            ft.Row(
                spacing=10,
                controls=[
                    ft.Button(
                        "Import Files",
                        icon=ft.Icons.UPLOAD_FILE,
                        on_click=on_import_files_click,
                    ),
                    ft.Button(
                        "Import Folder",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=on_import_folder_click,
                    ),
                ],
            ),
        ],
    )
