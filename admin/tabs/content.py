"""Pestaña · Biblioteca de contenido publicado."""

from __future__ import annotations

import re
from pathlib import Path

import flet as ft

from .. import branding, theme as t, widgets
from ..content import existing_files, load_document
from ..context import AppContext

KIND_FILTERS = [("all", "Todos"), ("repos", "Repositorios"), ("guias", "Guías")]


class ContentTab:
    """Lista, abre, abre en el navegador y elimina publicaciones."""

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self.items: list[dict] = []
        self.query = ""
        self.kind_filter = "all"
        self._build()
        self.view = self._compose()

    def on_mount(self) -> None:
        self.reload()

    # ------------------------------------------------------------------ datos
    def reload(self) -> None:
        self.items = self._scan()
        self._render()

    def _scan(self) -> list[dict]:
        found: list[dict] = []
        for kind in ("repos", "guias"):
            for path in existing_files(self.ctx.settings.project_root, kind):
                try:
                    draft = load_document(path)
                except (OSError, ValueError):
                    continue
                found.append(
                    {
                        "path": path,
                        "title": draft.title,
                        "kind": draft.kind,
                        "category": draft.category,
                        "level": draft.level,
                        "updated": draft.updated,
                        "slug": draft.final_slug,
                        "url": self.ctx.settings.site_url + draft.public_path,
                        "words": len(re.findall(r"\w+", draft.body)),
                    }
                )
        found.sort(key=lambda item: item["updated"], reverse=True)
        return found

    # ------------------------------------------------------------------ controles
    def _build(self) -> None:
        self.search = widgets.field(
            "Buscar",
            hint="título, slug o categoría…",
            prefix_icon=ft.Icons.SEARCH,
        )
        self.search.on_change = lambda _e: self._render()
        self.search.expand = True

        self.kind_chips = {
            key: widgets.selectable_chip(
                label,
                key == self.kind_filter,
                lambda _e, k=key: self._set_kind(k),
            )
            for key, label in KIND_FILTERS
        }

        self.counter = ft.Text("—", size=11, color=t.DIM)
        self.holder = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    def _compose(self) -> ft.Control:
        header = widgets.panel_header(
            "Contenido publicado",
            "Todo lo que ya está en el sitio. Abre, edita o elimina sin tocar archivos a mano.",
            icon=ft.Icons.LIBRARY_BOOKS,
            actions=[
                widgets.ghost_button(
                    "Nuevo", ft.Icons.ADD, lambda _e: self._new()
                ),
                widgets.icon_button(
                    ft.Icons.REFRESH, lambda _e: self.reload(), tooltip="Recargar"
                ),
            ],
        )

        toolbar = widgets.card(
            ft.Row(
                [
                    self.search,
                    ft.Row(list(self.kind_chips.values()), spacing=6),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=(14, 12),
        )

        return ft.Column(
            [header, toolbar, self.counter, self.holder],
            spacing=14,
            expand=True,
        )

    def _set_kind(self, key: str) -> None:
        self.kind_filter = key
        for name, chip in self.kind_chips.items():
            widgets.set_chip_selected(chip, name == key)
            widgets.safe_update(chip)
        self._render()

    # ------------------------------------------------------------------ render
    def _filtered(self) -> list[dict]:
        term = (self.search.value or "").strip().lower()
        result = []
        for item in self.items:
            if self.kind_filter != "all" and item["kind"] != self.kind_filter:
                continue
            if term:
                blob = f"{item['title']} {item['slug']} {item['category']}".lower()
                if term not in blob:
                    continue
            result.append(item)
        return result

    def _render(self) -> None:
        items = self._filtered()
        total = len(self.items)
        self.counter.value = (
            f"{len(items)} de {total} publicaciones" if len(items) != total else f"{total} publicaciones"
        )
        self.counter.color = t.DIM

        if not items:
            self.holder.controls = [
                widgets.empty_state(
                    "Sin resultados" if total else "Todavía no hay contenido",
                    "Prueba con otra búsqueda."
                    if total
                    else "Crea el primer repositorio o guía desde el editor.",
                    icon=ft.Icons.LIBRARY_BOOKS,
                    accent=t.CYAN,
                    action=widgets.ghost_button(
                        "Ir al editor", ft.Icons.EDIT_NOTE, lambda _e: self._new()
                    ),
                )
            ]
            widgets.safe_update(self.holder)
            widgets.safe_update(self.counter)
            return

        self.holder.controls = [self._table(items)]
        widgets.safe_update(self.holder)
        widgets.safe_update(self.counter)

    def _table(self, items: list[dict]) -> ft.Control:
        head = ft.TextStyle(size=10.5, weight=ft.FontWeight.W_700, color=t.DIM)

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=64, content=ft.Text("Tipo", style=head)),
                    ft.Container(expand=True, content=ft.Text("Título", style=head)),
                    ft.Container(width=130, content=ft.Text("Categoría", style=head)),
                    ft.Container(width=95, content=ft.Text("Nivel", style=head)),
                    ft.Container(width=100, content=ft.Text("Actualizado", style=head)),
                    ft.Container(width=132, content=ft.Text("Acciones", style=head)),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            bgcolor=t.alpha("#FFFFFF", 0.02),
            border=ft.Border.only(bottom=ft.BorderSide(1, t.BORDER)),
        )

        rows = [header]
        for item in items:
            rows.append(self._row(item))

        return ft.Container(
            content=ft.Column(rows, spacing=0),
            bgcolor=t.SURFACE,
            border=ft.Border.all(1, t.BORDER),
            border_radius=ft.BorderRadius.all(14),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )

    def _row(self, item: dict) -> ft.Control:
        category = branding.CATEGORIES.get(item["category"])
        is_repo = item["kind"] == "repos"

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=64,
                        content=widgets.badge(
                            "Repo" if is_repo else "Guía",
                            color=t.CYAN if is_repo else t.YELLOW,
                        ),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                item["title"],
                                size=12.5,
                                weight=ft.FontWeight.W_600,
                                color=t.TEXT,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                item["slug"],
                                size=10.5,
                                color=t.DIM,
                                font_family=t.mono_font(),
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=2,
                        tight=True,
                        expand=True,
                    ),
                    ft.Container(
                        width=130,
                        content=ft.Text(
                            category.label if category else item["category"],
                            size=12,
                            color=category.accent if category else t.MUTED,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ),
                    ft.Container(
                        width=95,
                        content=ft.Text(item["level"], size=11.5, color=t.MUTED,
                                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ),
                    ft.Container(
                        width=100,
                        content=ft.Text(
                            item["updated"],
                            size=11.5,
                            color=t.DIM,
                            font_family=t.mono_font(),
                        ),
                    ),
                    ft.Container(
                        width=132,
                        content=ft.Row(
                            [
                                widgets.icon_button(
                                    ft.Icons.EDIT,
                                    lambda _e, it=item: self._edit(it),
                                    tooltip="Editar",
                                ),
                                widgets.icon_button(
                                    ft.Icons.OPEN_IN_NEW,
                                    lambda _e, it=item: self._open(it),
                                    tooltip="Ver en el sitio",
                                ),
                                widgets.icon_button(
                                    ft.Icons.DELETE_OUTLINE,
                                    lambda _e, it=item: self._confirm_delete(it),
                                    tooltip="Eliminar",
                                    color=t.DANGER,
                                ),
                            ],
                            spacing=0,
                            tight=True,
                        ),
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border=ft.Border.only(bottom=ft.BorderSide(1, t.BORDER_SOFT)),
        )

    # ------------------------------------------------------------------ acciones
    def _new(self) -> None:
        if self.ctx.open_editor:
            self.ctx.open_editor(None)

    def _edit(self, item: dict) -> None:
        if self.ctx.open_editor:
            self.ctx.open_editor(item["path"])

    def _open(self, item: dict) -> None:
        try:
            self.ctx.page.launch_url(item["url"])
        except (AttributeError, RuntimeError):
            self.ctx.toast("No se pudo abrir el navegador.", "error")

    def _confirm_delete(self, item: dict) -> None:
        def do_delete(_event: ft.Event) -> None:
            try:
                Path(item["path"]).unlink()
            except OSError as exc:
                self.ctx.page.pop_dialog()
                self.ctx.toast(f"No se pudo eliminar: {exc}", "error")
                return

            self.ctx.page.pop_dialog()
            self.ctx.toast(
                f"{item['path'].name} eliminado. Publica para quitarlo del sitio.",
                "warn",
            )
            self.reload()

        body = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Eliminar publicación",
                        size=16,
                        weight=ft.FontWeight.W_700,
                        color=t.TEXT,
                    ),
                    ft.Text(
                        f"Se borrará {Path(item['path']).name} del proyecto. "
                        "La página seguirá visible en el sitio hasta que publiques "
                        "los cambios.",
                        size=13,
                        color=t.MUTED,
                    ),
                    ft.Row(
                        [
                            ft.TextButton(
                                "Cancelar",
                                on_click=lambda _e: self.ctx.page.pop_dialog(),
                                style=ft.ButtonStyle(color=t.MUTED),
                            ),
                            ft.TextButton(
                                "Eliminar",
                                on_click=do_delete,
                                style=ft.ButtonStyle(color=t.DANGER),
                            ),
                        ],
                        spacing=4,
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=14,
                tight=True,
            ),
            bgcolor=t.SURFACE_ALT,
            padding=ft.Padding.all(24),
            border_radius=ft.BorderRadius.all(16),
            border=ft.Border.all(1, t.BORDER),
            width=520,
        )

        dialog = ft.AlertDialog(
            modal=True,
            content=body,
            content_padding=0,
            bgcolor=t.SURFACE_ALT,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
        self.ctx.page.show_dialog(dialog)
