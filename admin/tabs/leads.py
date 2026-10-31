"""Pestaña 3 · Leads y suscriptores."""

from __future__ import annotations

import csv
from datetime import datetime

import flet as ft

from .. import theme as t, widgets
from ..context import AppContext
from ..supabase_api import SupabaseError

STATUS_COLORS = {
    "nuevo": t.CYAN,
    "activo": t.BRAND,
    "baja": t.DANGER,
    "bounced": t.DANGER,
}

MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def human_date(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return str(value or "—")[:16]
    return f"{parsed.day} {MONTHS[parsed.month - 1]} {parsed.year} · {parsed:%H:%M}"


class LeadsTab:
    """Tabla de correos capturados con búsqueda y exportación."""

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self.rows: list[dict] = []
        self.error: str | None = None
        self.loading = False
        self._build()
        self.view = self._compose()

    def on_mount(self) -> None:
        """Se llama cuando la vista ya está montada en la página."""
        self.refresh()

    # ------------------------------------------------------------------ controles
    def _build(self) -> None:
        self.search = widgets.field(
            "Buscar",
            hint="correo o fuente…",
            prefix_icon=ft.Icons.SEARCH,
            on_change=None,
        )
        self.search.on_submit = lambda _e: self.refresh()
        self.search.expand = True

        self.counter = ft.Text("—", size=11, color=t.DIM)
        self.table_holder = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        self.stats_row = ft.Row(spacing=12)

    # ------------------------------------------------------------------ layout
    def _compose(self) -> ft.Control:
        header = widgets.panel_header(
            "Leads y correos",
            "Suscriptores capturados en el sitio, listos para exportar.",
            icon=ft.Icons.EMAIL,
            actions=[
                widgets.ghost_button(
                    "Exportar CSV", ft.Icons.DOWNLOAD, self._export_csv
                ),
                widgets.icon_button(
                    ft.Icons.REFRESH, lambda _e: self.refresh(), tooltip="Actualizar"
                ),
            ],
        )

        toolbar = widgets.card(
            ft.Row(
                [
                    self.search,
                    widgets.primary_button(
                        "Buscar", ft.Icons.SEARCH, lambda _e: self.refresh()
                    ),
                    widgets.ghost_button(
                        "Limpiar",
                        ft.Icons.CLOSE,
                        self._clear_search,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=(14, 12),
        )

        return ft.Column(
            [
                header,
                toolbar,
                self.stats_row,
                self.counter,
                self.table_holder,
            ],
            spacing=14,
            expand=True,
        )

    # ------------------------------------------------------------------ datos
    def _clear_search(self, _event: ft.Event) -> None:
        self.search.value = ""
        self.search.update()
        self.refresh()

    def refresh(self) -> None:
        if self.loading:
            return
        self.loading = True
        self._render_loading()
        self.ctx.page.run_thread(self._load)

    def _load(self) -> None:
        try:
            if self.ctx.supabase is None:
                raise SupabaseError(
                    "Supabase no está configurado. Crea admin/.env con SUPABASE_URL "
                    "y SUPABASE_SERVICE_KEY."
                )
            self.rows = self.ctx.supabase.leads(search=self.search.value or "")
            self.error = None
        except SupabaseError as exc:
            self.rows = []
            self.error = str(exc)
        except Exception as exc:  # noqa: BLE001
            self.rows = []
            self.error = f"Error inesperado: {exc}"
        finally:
            self.loading = False
            self._render()

    # ------------------------------------------------------------------ render
    def _render_loading(self) -> None:
        self.table_holder.controls = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(width=16, height=16, stroke_width=2, color=t.BRAND),
                        ft.Text("Consultando suscriptores…", size=12.5, color=t.MUTED),
                    ],
                    spacing=12,
                ),
                padding=40,
                alignment=ft.Alignment.CENTER,
            )
        ]
        self._safe_update(self.table_holder)

    def _render(self) -> None:
        if self.error:
            self.stats_row.controls = []
            self.counter.value = "Error de conexión"
            self.counter.color = t.DANGER
            self.table_holder.controls = [
                widgets.empty_state(
                    "No se pudieron leer los leads",
                    self.error,
                    icon=ft.Icons.CLOUD_OFF,
                    accent=t.DANGER,
                    action=widgets.ghost_button(
                        "Reintentar", ft.Icons.REFRESH, lambda _e: self.refresh()
                    ),
                )
            ]
            self._flush()
            return

        total = len(self.rows)
        news = len([row for row in self.rows if str(row.get("status", "")).lower() == "nuevo"])
        sources = {str(row.get("source") or "directo") for row in self.rows}
        latest = self.rows[0].get("created_at") if self.rows else None

        self.stats_row.controls = [
            widgets.kpi("Suscriptores", str(total), icon=ft.Icons.GROUPS, accent=t.BRAND,
                        hint="en la consulta actual"),
            widgets.kpi("Nuevos", str(news), icon=ft.Icons.FIBER_NEW, accent=t.CYAN,
                        hint="estado 'nuevo'"),
            widgets.kpi("Fuentes", str(len(sources)), icon=ft.Icons.HUB, accent=t.YELLOW,
                        hint="orígenes distintos"),
            widgets.kpi("Último registro", human_date(latest) if latest else "—",
                        icon=ft.Icons.SCHEDULE, accent=t.BRAND, hint="más reciente"),
        ]

        self.counter.value = f"{total} registros" if total else "Sin resultados"
        self.counter.color = t.DIM

        if not self.rows:
            self.table_holder.controls = [
                widgets.empty_state(
                    "Todavía no hay suscriptores",
                    "Cuando el formulario del sitio guarde correos en la tabla leads, "
                    "aparecerán en esta lista.",
                    icon=ft.Icons.MARK_EMAIL_UNREAD,
                    accent=t.CYAN,
                )
            ]
            self._flush()
            return

        self.table_holder.controls = [self._table()]
        self._flush()

    def _table(self) -> ft.Control:
        header_style = ft.TextStyle(size=10.5, weight=ft.FontWeight.W_700, color=t.DIM)

        rows: list[ft.DataRow] = []
        for row in self.rows:
            status = str(row.get("status") or "nuevo").lower()
            color = STATUS_COLORS.get(status, t.MUTED)
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                str(row.get("email") or "—"),
                                size=12.5,
                                color=t.TEXT,
                                font_family=t.mono_font(),
                            )
                        ),
                        ft.DataCell(
                            ft.Text(str(row.get("source") or "directo"), size=12, color=t.MUTED)
                        ),
                        ft.DataCell(widgets.badge(status, color=color)),
                        ft.DataCell(
                            ft.Text(human_date(row.get("created_at", "")), size=11.5, color=t.DIM)
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Correo", style=header_style)),
                ft.DataColumn(ft.Text("Origen", style=header_style)),
                ft.DataColumn(ft.Text("Estado", style=header_style)),
                ft.DataColumn(ft.Text("Alta", style=header_style)),
            ],
            rows=rows,
            column_spacing=34,
            heading_row_height=42,
            data_row_min_height=48,
            data_row_max_height=52,
            divider_thickness=1,
            horizontal_lines=ft.BorderSide(1, t.BORDER_SOFT),
            heading_row_color=t.alpha("#FFFFFF", 0.02),
            border_radius=ft.BorderRadius.all(12),
        )

        return ft.Container(
            content=ft.Row([table], scroll=ft.ScrollMode.AUTO),
            padding=ft.Padding.symmetric(horizontal=6, vertical=6),
            bgcolor=t.SURFACE,
            border=ft.Border.all(1, t.BORDER),
            border_radius=ft.BorderRadius.all(14),
        )

    def _flush(self) -> None:
        for control in (self.stats_row, self.counter, self.table_holder):
            self._safe_update(control)

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        try:
            control.update()
        except (AssertionError, RuntimeError):
            pass

    # ------------------------------------------------------------------ export
    def _export_csv(self, _event: ft.Event) -> None:
        if not self.rows:
            self.ctx.toast("No hay datos para exportar.", "warn")
            return

        exports = self.ctx.settings.exports_dir
        exports.mkdir(parents=True, exist_ok=True)
        target = exports / f"leads-{datetime.now():%Y%m%d-%H%M%S}.csv"

        try:
            with target.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["email", "source", "status", "created_at"],
                    extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerows(self.rows)
        except OSError as exc:
            self.ctx.toast(f"No se pudo escribir el CSV: {exc}", "error")
            return

        self.ctx.toast(f"Exportado a {target.name}", "ok")
