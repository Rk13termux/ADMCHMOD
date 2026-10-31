"""Pestaña 2 · Analíticas de tráfico desde Supabase."""

from __future__ import annotations

from datetime import datetime

import flet as ft

from .. import theme as t, widgets
from ..analytics import AnalyticsSummary, summarize
from ..context import AppContext
from ..supabase_api import SupabaseError


PERIODS = [(7, "7 días"), (30, "30 días"), (90, "90 días")]


class AnalyticsTab:
    """KPIs, serie diaria y ranking de páginas."""

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self.period = 30
        self.summary: AnalyticsSummary | None = None
        self.error: str | None = None
        self.loading = False
        self._build()
        self.view = self._compose()

    def on_mount(self) -> None:
        """Se llama cuando la vista ya está montada en la página."""
        self.refresh()

    # ------------------------------------------------------------------ controles
    def _build(self) -> None:
        self.chips = {days: self._chip(label, days) for days, label in PERIODS}
        self.updated_text = ft.Text("Sin datos todavía", size=11, color=t.DIM)
        self.body = ft.Column(spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    def _chip(self, label: str, days: int) -> ft.Container:
        selected = days == self.period
        return ft.Container(
            content=ft.Text(
                label,
                size=12,
                weight=ft.FontWeight.W_600,
                color=t.ON_BRAND if selected else t.MUTED,
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            bgcolor=t.BRAND if selected else t.alpha("#FFFFFF", 0.03),
            border=ft.Border.all(1, t.BRAND if selected else t.BORDER),
            border_radius=ft.BorderRadius.all(999),
            on_click=lambda _e, d=days: self._select_period(d),
            ink=True,
        )

    def _select_period(self, days: int) -> None:
        if days == self.period:
            return
        self.period = days
        for value, chip in self.chips.items():
            selected = value == days
            chip.bgcolor = t.BRAND if selected else t.alpha("#FFFFFF", 0.03)
            chip.border = ft.Border.all(1, t.BRAND if selected else t.BORDER)
            chip.content.color = t.ON_BRAND if selected else t.MUTED
            chip.update()
        self.refresh()

    # ------------------------------------------------------------------ layout
    def _compose(self) -> ft.Control:
        header = widgets.panel_header(
            "Analíticas",
            "Visitas y tráfico real de chmodxcode.pro, leídos de Supabase.",
            icon=ft.Icons.INSIGHTS,
            actions=[
                ft.Row(list(self.chips.values()), spacing=6),
                widgets.icon_button(
                    ft.Icons.REFRESH, lambda _e: self.refresh(), tooltip="Actualizar"
                ),
            ],
        )

        return ft.Column(
            [
                header,
                self.updated_text,
                self.body,
            ],
            spacing=14,
            expand=True,
        )

    # ------------------------------------------------------------------ datos
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
            rows = self.ctx.supabase.page_views(self.period)
            self.summary = summarize(rows, self.period)
            self.error = None
        except SupabaseError as exc:
            self.summary = None
            self.error = str(exc)
        except Exception as exc:  # noqa: BLE001 - la UI nunca debe romperse
            self.summary = None
            self.error = f"Error inesperado: {exc}"
        finally:
            self.loading = False
            self._render()

    # ------------------------------------------------------------------ render
    def _render_loading(self) -> None:
        self.body.controls = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(width=16, height=16, stroke_width=2, color=t.BRAND),
                        ft.Text("Consultando Supabase…", size=12.5, color=t.MUTED),
                    ],
                    spacing=12,
                ),
                padding=40,
                alignment=ft.Alignment.CENTER,
            )
        ]
        self._safe_update(self.body)

    def _render(self) -> None:
        if self.error:
            self.updated_text.value = "Error de conexión"
            self.updated_text.color = t.DANGER
            self.body.controls = [
                widgets.empty_state(
                    "No se pudieron leer las métricas",
                    self.error,
                    icon=ft.Icons.CLOUD_OFF,
                    accent=t.DANGER,
                    action=widgets.ghost_button(
                        "Reintentar", ft.Icons.REFRESH, lambda _e: self.refresh()
                    ),
                )
            ]
            self._safe_update(self.updated_text)
            self._safe_update(self.body)
            return

        summary = self.summary or AnalyticsSummary()
        now = datetime.now().strftime("%H:%M:%S")
        self.updated_text.value = (
            f"{summary.rows} eventos · actualizado a las {now} · últimos {self.period} días"
        )
        self.updated_text.color = t.DIM

        if summary.rows == 0:
            self.body.controls = [
                widgets.empty_state(
                    "Todavía no hay visitas registradas",
                    "Cuando el sitio empiece a enviar eventos a la tabla page_views, "
                    "las métricas aparecerán aquí automáticamente.",
                    icon=ft.Icons.QUERY_STATS,
                    accent=t.CYAN,
                )
            ]
            self._safe_update(self.updated_text)
            self._safe_update(self.body)
            return

        kpis = ft.Row(
            [
                widgets.kpi(
                    "Visitas",
                    f"{summary.total_views:,}".replace(",", "."),
                    icon=ft.Icons.VISIBILITY,
                    accent=t.BRAND,
                    hint=f"media {summary.daily_average:.1f}/día activo",
                ),
                widgets.kpi(
                    "Visitantes únicos",
                    f"{summary.unique_visitors:,}".replace(",", "."),
                    icon=ft.Icons.PEOPLE,
                    accent=t.CYAN,
                    hint="identificados por visitor_id",
                ),
                widgets.kpi(
                    "Vistas a la academia",
                    f"{summary.academy_views:,}".replace(",", "."),
                    icon=ft.Icons.SCHOOL,
                    accent=t.YELLOW,
                    hint=f"{summary.academy_from_cta} desde un CTA",
                ),
                widgets.kpi(
                    "Conversión",
                    f"{summary.conversion:.1f}%",
                    icon=ft.Icons.TRENDING_UP,
                    accent=t.BRAND,
                    hint="academia / total",
                ),
            ],
            spacing=12,
        )

        chart_card = widgets.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Visitas por día",
                                size=13,
                                weight=ft.FontWeight.W_700,
                                color=t.TEXT,
                            ),
                            ft.Container(expand=True),
                            widgets.pill(f"máx {max((c for _, c in summary.days), default=0)}/día"),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self._chart(summary.days),
                ],
                spacing=16,
            )
        )

        pages_card = widgets.card(
            ft.Column(
                [
                    ft.Text(
                        "Páginas más vistas",
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=t.TEXT,
                    ),
                    ft.Column(
                        [
                            widgets.bar_row(path, count, summary.pages[0][1], width=190)
                            for path, count in summary.pages
                        ],
                        spacing=10,
                    ),
                ],
                spacing=16,
            ),
            expand=3,
        )

        sources_card = widgets.card(
            ft.Column(
                [
                    ft.Text(
                        "Origen del tráfico",
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=t.TEXT,
                    ),
                    ft.Column(
                        [
                            widgets.bar_row(name, count, summary.sources[0][1],
                                            accent=t.CYAN, width=150)
                            for name, count in summary.sources
                        ],
                        spacing=10,
                    ),
                ],
                spacing=16,
            )
        )

        devices_card = widgets.card(
            ft.Column(
                [
                    ft.Text(
                        "Dispositivos",
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=t.TEXT,
                    ),
                    ft.Column(
                        [
                            widgets.bar_row(name, count, summary.devices[0][1],
                                            accent=t.YELLOW, width=150)
                            for name, count in summary.devices
                        ],
                        spacing=10,
                    ),
                ],
                spacing=16,
            )
        )

        blocks: list[ft.Control] = [
            kpis,
            chart_card,
            ft.Row(
                [
                    pages_card,
                    ft.Column([sources_card, devices_card], spacing=16, expand=2),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ]

        if summary.has_utm:
            blocks.append(self._cta_card(summary))
        elif summary.rows:
            blocks.append(
                widgets.card(
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=15, color=t.YELLOW),
                            ft.Text(
                                "Aún no hay datos de atribución. Ejecuta "
                                "admin/sql/002_tracking.sql para medir qué artículo "
                                "y qué CTA llevan a la academia.",
                                size=12,
                                color=t.MUTED,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    border_color=t.alpha(t.YELLOW, 0.30),
                )
            )

        self.body.controls = blocks
        self._safe_update(self.updated_text)
        self._safe_update(self.body)

    def _cta_card(self, summary: AnalyticsSummary) -> ft.Control:
        maximum = max(count for _, count in summary.cta_blocks) or 1
        rows = [
            widgets.bar_row(label, count, maximum, accent=t.YELLOW, width=210)
            for label, count in summary.cta_blocks
        ]

        footer: list[ft.Control] = []
        if summary.cta_campaigns:
            top = summary.cta_campaigns[0]
            footer.append(
                ft.Text(
                    f"Artículo que más convierte: {top[0]} ({top[1]})",
                    size=11,
                    color=t.DIM,
                )
            )

        return widgets.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Qué CTA lleva a la academia",
                                size=13,
                                weight=ft.FontWeight.W_700,
                                color=t.TEXT,
                            ),
                            ft.Container(expand=True),
                            widgets.pill(f"{summary.academy_from_cta} llegadas", color=t.YELLOW),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(rows, spacing=10),
                    *footer,
                ],
                spacing=16,
            )
        )

    # ------------------------------------------------------------------ gráfico
    def _chart(self, days: list[tuple[str, int]]) -> ft.Control:
        maximum = max((count for _, count in days), default=0) or 1
        columns: list[ft.Control] = []

        for index, (day, count) in enumerate(days):
            height = max(3, round(120 * count / maximum))
            show_label = index % max(1, len(days) // 8) == 0 or index == len(days) - 1
            columns.append(
                ft.Column(
                    [
                        ft.Text(
                            str(count) if count else "",
                            size=9,
                            color=t.MUTED,
                            height=12,
                        ),
                        ft.Container(
                            width=11,
                            height=height,
                            bgcolor=t.BRAND if count else t.alpha("#FFFFFF", 0.06),
                            border_radius=ft.BorderRadius.vertical(top=3, bottom=3),
                            tooltip=f"{day}: {count} visitas",
                        ),
                        ft.Text(
                            day[5:] if show_label else "",
                            size=9,
                            color=t.DIM,
                            height=14,
                        ),
                    ],
                    spacing=3,
                    expand=True,
                    alignment=ft.MainAxisAlignment.END,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

        return ft.Container(
            content=ft.Row(
                columns,
                spacing=3,
                height=170,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
            padding=ft.Padding.only(top=8),
        )

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        try:
            control.update()
        except (AssertionError, RuntimeError):
            pass
