"""Ventana principal del panel: cabecera, pestañas y barra de estado."""

from __future__ import annotations

import os
from pathlib import Path

import flet as ft

from . import __version__, theme as t, widgets
from .config import Settings, load_settings, mask_secret
from .context import AppContext
from .supabase_api import SupabaseClient, SupabaseError
from .context import TAB_CONTENT, TAB_EDITOR, TAB_PUBLISH
from .tabs.analytics import AnalyticsTab
from .tabs.content import ContentTab
from .tabs.editor import EditorTab
from .tabs.leads import LeadsTab
from .tabs.publish import PublishTab

WINDOW_WIDTH = int(os.environ.get("CHMODX_WINDOW_WIDTH", "1280"))
WINDOW_HEIGHT = int(os.environ.get("CHMODX_WINDOW_HEIGHT", "800"))


class AdminApp:
    """Ensambla la aplicación completa."""

    def __init__(self, page: ft.Page, settings: Settings) -> None:
        self.page = page
        self.settings = settings
        self.ctx = AppContext(page=page, settings=settings)
        self.supabase_error: str | None = None

        if settings.supabase_ready:
            try:
                self.ctx.supabase = SupabaseClient(
                    settings.supabase_url, settings.read_key
                )
            except SupabaseError as exc:
                self.supabase_error = str(exc)

        self.editor = EditorTab(self.ctx)
        self.content = ContentTab(self.ctx)
        self.analytics = AnalyticsTab(self.ctx)
        self.leads = LeadsTab(self.ctx)
        self.publish = PublishTab(self.ctx)
        self.tabs_list = [
            self.editor,
            self.content,
            self.analytics,
            self.leads,
            self.publish,
        ]

        self.ctx.go_to_tab = self.go_to_tab
        self.ctx.open_editor = self.open_editor

    # ------------------------------------------------------------------ montaje
    def mount(self) -> None:
        page = self.page
        page.title = "CHMODX · Panel de Administración Pro"
        page.theme_mode = ft.ThemeMode.DARK
        page.theme = t.build_theme()
        page.bgcolor = t.BG
        page.padding = 0
        page.spacing = 0
        t.register_fonts(page)

        try:
            page.window.width = WINDOW_WIDTH
            page.window.height = WINDOW_HEIGHT
            page.window.min_width = 1100
            page.window.min_height = 720
            icon = t.logo_icon()
            if icon:
                page.window.icon = icon
        except (AttributeError, RuntimeError):
            # En modo web la ventana no existe: se ignora.
            pass

        page.add(self._header(), self._tabs(), self._status_bar())
        page.update()

        for tab in self.tabs_list:
            handler = getattr(tab, "on_mount", None)
            if callable(handler):
                handler()

        if self.ctx.supabase is not None:
            page.run_thread(self._probe_supabase)

    def _probe_supabase(self) -> None:
        """Comprueba el acceso a las tablas y avisa si RLS lo bloquea."""
        if self.ctx.supabase is None:
            return
        broken = [status for status in self.ctx.supabase.probe() if not status.ok]
        if broken:
            self.ctx.toast(broken[0].detail, "error")

    # ------------------------------------------------------------------ cabecera
    def _brand(self) -> ft.Control:
        return ft.Row(
            [
                self._brand_mark(),
                ft.Column(
                    [
                        ft.Text(
                            "CHMODX",
                            size=15,
                            weight=ft.FontWeight.W_800,
                            color=t.TEXT,
                            font_family=t.display_font(),
                        ),
                        ft.Text(
                            "Panel de Administración Pro",
                            size=10.5,
                            color=t.DIM,
                        ),
                    ],
                    spacing=0,
                    tight=True,
                ),
            ],
            spacing=11,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _brand_mark(self) -> ft.Control:
        """Logo de la marca, con la caja ``CX`` como respaldo."""
        source = t.logo_source()
        if source:
            return ft.Image(
                src=source,
                width=40,
                height=40,
                fit=ft.BoxFit.CONTAIN,
                semantics_label="CHMODX",
            )

        return ft.Container(
            content=ft.Text(
                "CX",
                size=15,
                weight=ft.FontWeight.W_800,
                color=t.ON_BRAND,
                font_family=t.mono_font(),
            ),
            width=38,
            height=38,
            alignment=ft.Alignment.CENTER,
            bgcolor=t.BRAND,
            border_radius=ft.BorderRadius.all(10),
        )

    def _header(self) -> ft.Control:
        settings = self.settings

        if self.ctx.supabase is not None:
            supabase_pill = widgets.pill(
                f"Supabase · {'service' if settings.uses_service_key else 'anon'}",
                color=t.BRAND,
            )
        else:
            supabase_pill = widgets.pill("Supabase sin configurar", color=t.DANGER)

        git_pill = widgets.pill(f"git · {settings.git_branch}", color=t.CYAN)
        path_pill = widgets.pill(settings.project_root.name, color=t.MUTED)

        right = ft.Row(
            [supabase_pill, git_pill, path_pill],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=ft.Row(
                [self._brand(), ft.Container(expand=True), right],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=22, vertical=14),
            bgcolor=t.SURFACE,
            border=ft.Border.only(bottom=ft.BorderSide(1, t.BORDER)),
        )

    # ------------------------------------------------------------------ pestañas
    def _tabs(self) -> ft.Control:
        bar = ft.TabBar(
            tabs=[
                ft.Tab(label="Editor", icon=ft.Icons.EDIT_NOTE),
                ft.Tab(label="Contenido", icon=ft.Icons.LIBRARY_BOOKS),
                ft.Tab(label="Analíticas", icon=ft.Icons.INSIGHTS),
                ft.Tab(label="Leads", icon=ft.Icons.EMAIL),
                ft.Tab(label="Publicación", icon=ft.Icons.CLOUD_UPLOAD),
            ],
            indicator_color=t.BRAND,
            label_color=t.TEXT,
            unselected_label_color=t.MUTED,
            divider_color=t.BORDER_SOFT,
        )

        views = ft.TabBarView(
            controls=[
                ft.Container(content=tab.view, expand=True,
                             padding=ft.Padding.symmetric(horizontal=22, vertical=18))
                for tab in self.tabs_list
            ],
            expand=True,
        )

        self.tabs = ft.Tabs(
            length=len(self.tabs_list),
            selected_index=0,
            content=ft.Column([bar, views], expand=True, spacing=0),
            expand=True,
            on_change=self._on_tab_change,
        )
        return self.tabs

    def _on_tab_change(self, event: ft.Event) -> None:
        index = self.tabs.selected_index or 0
        if index == TAB_CONTENT:
            self.content.reload()
        elif index == TAB_PUBLISH:
            self.publish.sync()

    def go_to_tab(self, index: int) -> None:
        if not 0 <= index < len(self.tabs_list):
            return
        self.tabs.selected_index = index
        try:
            self.tabs.update()
        except (AssertionError, RuntimeError):
            pass
        if index == TAB_CONTENT:
            self.content.reload()
        elif index == TAB_PUBLISH:
            self.publish.sync()

    def open_editor(self, path: Path | None) -> None:
        """Abre una publicación en el editor, o una hoja en blanco."""
        if path is None:
            self.editor.new_document()
        else:
            self.editor.load_path(path)
        self.go_to_tab(TAB_EDITOR)

    # ------------------------------------------------------------------ estado
    def _status_bar(self) -> ft.Control:
        settings = self.settings
        env = ", ".join(path.name for path in settings.env_files) or "sin .env"

        left = ft.Row(
            [
                ft.Text(f"v{__version__}", size=10.5, color=t.DIM,
                        font_family=t.mono_font()),
                ft.Text("·", size=10.5, color=t.BORDER),
                ft.Text(f"entorno: {env}", size=10.5, color=t.DIM),
                ft.Text("·", size=10.5, color=t.BORDER),
                ft.Text(
                    f"clave {mask_secret(settings.read_key)}",
                    size=10.5,
                    color=t.DIM,
                    font_family=t.mono_font(),
                ),
            ],
            spacing=8,
        )

        right = ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER_OPEN, size=12, color=t.DIM),
                ft.Text(
                    str(settings.project_root),
                    size=10.5,
                    color=t.DIM,
                    font_family=t.mono_font(),
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=6,
        )

        return ft.Container(
            content=ft.Row(
                [left, ft.Container(expand=True), right],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=22, vertical=8),
            bgcolor=t.SURFACE,
            border=ft.Border.only(top=ft.BorderSide(1, t.BORDER_SOFT)),
        )


def run(*, web: bool = False, host: str = "127.0.0.1", port: int = 8560) -> None:
    """Arranca la aplicación.

    Por defecto abre una ventana de escritorio. Con ``web=True`` sirve la misma
    interfaz en el navegador, útil para probar o para entrar desde el móvil en
    la red local.
    """
    settings = load_settings()

    def main(page: ft.Page) -> None:
        AdminApp(page, settings).mount()

    if web:
        ft.run(
            main,
            view=ft.AppView.FLET_APP_WEB,
            host=host,
            port=port,
            assets_dir=str(t.ASSETS_DIR),
        )
    else:
        ft.run(main, assets_dir=str(t.ASSETS_DIR))
