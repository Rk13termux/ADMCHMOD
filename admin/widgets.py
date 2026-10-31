"""Componentes reutilizables de la interfaz."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from . import theme as t


# --------------------------------------------------------------------------- #
# Contenedores
# --------------------------------------------------------------------------- #
def card(
    content: ft.Control,
    *,
    padding: int | tuple[int, int] = 20,
    bgcolor: str = t.SURFACE,
    border_color: str = t.BORDER,
    expand: bool | int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> ft.Container:
    if isinstance(padding, tuple):
        pad = ft.Padding.symmetric(horizontal=padding[0], vertical=padding[1])
    else:
        pad = ft.Padding.all(padding)

    return ft.Container(
        content=content,
        padding=pad,
        bgcolor=bgcolor,
        border=ft.Border.all(1, border_color),
        border_radius=ft.BorderRadius.all(14),
        expand=expand,
        width=width,
        height=height,
    )


def panel_header(
    title: str,
    subtitle: str | None = None,
    *,
    icon: str | None = None,
    actions: list[ft.Control] | None = None,
) -> ft.Control:
    left: list[ft.Control] = []
    if icon:
        left.append(
            ft.Container(
                content=ft.Icon(icon, size=16, color=t.BRAND),
                width=32,
                height=32,
                alignment=ft.Alignment.CENTER,
                bgcolor=t.alpha(t.BRAND, 0.10),
                border=ft.Border.all(1, t.alpha(t.BRAND, 0.28)),
                border_radius=ft.BorderRadius.all(9),
            )
        )

    text_block = ft.Column(
        [
            ft.Text(
                title,
                size=17,
                weight=ft.FontWeight.W_700,
                color=t.TEXT,
                font_family=t.display_font(),
            ),
            *(
                [ft.Text(subtitle, size=12.5, color=t.MUTED)]
                if subtitle
                else []
            ),
        ],
        spacing=2,
        tight=True,
    )
    left.append(text_block)

    return ft.Row(
        [
            ft.Row(left, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row(actions or [], spacing=8),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def divider(height: int = 1, color: str = t.BORDER_SOFT) -> ft.Container:
    return ft.Container(height=height, bgcolor=color)


def spacer(height: float = 0, width: float = 0) -> ft.Container:
    return ft.Container(width=width or None, height=height or None)


# --------------------------------------------------------------------------- #
# Botones
# --------------------------------------------------------------------------- #
def primary_button(
    text: str,
    icon: str | None = None,
    on_click: Callable[[ft.Event], None] | None = None,
    *,
    disabled: bool = False,
    expand: bool = False,
    tooltip: str | None = None,
) -> ft.FilledButton:
    return ft.FilledButton(
        content=ft.Row(
            [
                *([ft.Icon(icon, size=16, color=t.ON_BRAND)] if icon else []),
                ft.Text(text, size=13.5, weight=ft.FontWeight.W_700, color=t.ON_BRAND),
            ],
            spacing=8,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=on_click,
        disabled=disabled,
        tooltip=tooltip,
        expand=expand,
        style=ft.ButtonStyle(
            bgcolor=t.BRAND,
            overlay_color=t.alpha("#000000", 0.10),
            padding=ft.Padding.symmetric(horizontal=18, vertical=14),
            shape=ft.RoundedRectangleBorder(radius=10),
            elevation=0,
        ),
    )


def ghost_button(
    text: str,
    icon: str | None = None,
    on_click: Callable[[ft.Event], None] | None = None,
    *,
    disabled: bool = False,
    accent: str = t.TEXT,
    tooltip: str | None = None,
) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        content=ft.Row(
            [
                *([ft.Icon(icon, size=15, color=accent)] if icon else []),
                ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=accent),
            ],
            spacing=7,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=on_click,
        disabled=disabled,
        tooltip=tooltip,
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, t.BORDER),
            bgcolor=t.alpha("#FFFFFF", 0.02),
            overlay_color=t.alpha(t.BRAND, 0.06),
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            shape=ft.RoundedRectangleBorder(radius=9),
        ),
    )


def icon_button(
    icon: str,
    on_click: Callable[[ft.Event], None] | None,
    *,
    tooltip: str = "",
    color: str = t.MUTED,
) -> ft.IconButton:
    return ft.IconButton(
        icon=icon,
        icon_color=color,
        icon_size=18,
        tooltip=tooltip,
        on_click=on_click,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            overlay_color=t.alpha(t.BRAND, 0.10),
        ),
    )


# --------------------------------------------------------------------------- #
# Etiquetas de estado
# --------------------------------------------------------------------------- #
def pill(text: str, *, color: str = t.BRAND, filled: bool = False) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    width=6,
                    height=6,
                    bgcolor=color,
                    border_radius=ft.BorderRadius.all(3),
                ),
                ft.Text(
                    text,
                    size=11,
                    weight=ft.FontWeight.W_600,
                    color=color if not filled else t.ON_BRAND,
                ),
            ],
            spacing=6,
            tight=True,
        ),
        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        bgcolor=color if filled else t.alpha(color, 0.08),
        border=ft.Border.all(1, color if filled else t.alpha(color, 0.30)),
        border_radius=ft.BorderRadius.all(999),
    )


def badge(text: str, *, color: str = t.CYAN) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            text.upper(),
            size=9.5,
            weight=ft.FontWeight.W_700,
            color=color,
        ),
        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
        bgcolor=t.alpha(color, 0.10),
        border=ft.Border.all(1, t.alpha(color, 0.28)),
        border_radius=ft.BorderRadius.all(6),
    )


# --------------------------------------------------------------------------- #
# Métricas
# --------------------------------------------------------------------------- #
def kpi(
    label: str,
    value: str,
    *,
    icon: str,
    accent: str = t.BRAND,
    hint: str | None = None,
) -> ft.Container:
    return card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(icon, size=15, color=accent),
                            width=30,
                            height=30,
                            alignment=ft.Alignment.CENTER,
                            bgcolor=t.alpha(accent, 0.10),
                            border_radius=ft.BorderRadius.all(8),
                        ),
                        ft.Text(label.upper(), size=10, weight=ft.FontWeight.W_700, color=t.DIM),
                    ],
                    spacing=10,
                ),
                ft.Text(
                    value,
                    size=28,
                    weight=ft.FontWeight.W_800,
                    color=t.TEXT,
                    font_family=t.display_font(),
                ),
                ft.Text(hint or " ", size=11, color=t.DIM),
            ],
            spacing=8,
        ),
        padding=18,
        expand=True,
    )


def bar_row(
    label: str,
    value: int,
    maximum: int,
    *,
    accent: str = t.BRAND,
    width: int = 210,
    suffix: str = "",
) -> ft.Row:
    ratio = (value / maximum) if maximum else 0
    filled = max(3, round(width * ratio))
    return ft.Row(
        [
            ft.Text(label, size=12, color=t.MUTED, width=150, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Stack(
                [
                    ft.Container(width=width, height=8, bgcolor=t.alpha("#FFFFFF", 0.05),
                                 border_radius=ft.BorderRadius.all(4)),
                    ft.Container(width=filled, height=8, bgcolor=accent,
                                 border_radius=ft.BorderRadius.all(4)),
                ],
                width=width,
                height=8,
            ),
            ft.Text(
                f"{value}{suffix}",
                size=12,
                weight=ft.FontWeight.W_600,
                color=t.TEXT,
                width=70,
                text_align=ft.TextAlign.RIGHT,
            ),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# --------------------------------------------------------------------------- #
# Formularios
# --------------------------------------------------------------------------- #
def field(
    label: str,
    *,
    value: str = "",
    hint: str | None = None,
    multiline: bool = False,
    min_lines: int = 1,
    max_lines: int = 1,
    on_change: Callable[[ft.Event], None] | None = None,
    prefix_icon: str | None = None,
    read_only: bool = False,
    helper: str | None = None,
    expand: bool = False,
) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value,
        hint_text=hint,
        multiline=multiline,
        min_lines=min_lines,
        max_lines=max_lines,
        on_change=on_change,
        prefix_icon=prefix_icon,
        read_only=read_only,
        helper=helper,
        expand=expand,
        text_size=13.5,
        color=t.TEXT,
        bgcolor=t.BG,
        border=ft.InputBorder.OUTLINE,
        border_color=t.BORDER,
        focused_border_color=t.BRAND,
        border_radius=ft.BorderRadius.all(9),
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        cursor_color=t.BRAND,
        selection_color=t.alpha(t.BRAND, 0.20),
        label_style=ft.TextStyle(size=12, color=t.MUTED),
        hint_style=ft.TextStyle(size=12.5, color=t.DIM),
        helper_style=ft.TextStyle(size=11, color=t.DIM),
        text_style=ft.TextStyle(size=13.5, color=t.TEXT, font_family=t.mono_font() if multiline else None),
    )


def dropdown(
    label: str,
    options: list[tuple[str, str]],
    value: str | None,
    on_select: Callable[[ft.Event], None] | None,
    *,
    expand: bool = True,
) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        options=[ft.DropdownOption(key=key, text=text) for key, text in options],
        on_select=on_select,
        expand=expand,
        text_size=13.5,
        color=t.TEXT,
        bgcolor=t.BG,
        border=ft.InputBorder.OUTLINE,
        border_color=t.BORDER,
        focused_border_color=t.BRAND,
        border_radius=ft.BorderRadius.all(9),
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=8),
        label_style=ft.TextStyle(size=12, color=t.MUTED),
        text_style=ft.TextStyle(size=13.5, color=t.TEXT),
        menu_style=ft.MenuStyle(
            bgcolor=t.SURFACE_ALT,
            side=ft.BorderSide(1, t.BORDER),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )


def empty_state(
    title: str,
    message: str,
    *,
    icon: str = ft.Icons.INFO_OUTLINE,
    action: ft.Control | None = None,
    accent: str = t.CYAN,
) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(icon, size=24, color=accent),
                    width=52,
                    height=52,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=t.alpha(accent, 0.08),
                    border=ft.Border.all(1, t.alpha(accent, 0.24)),
                    border_radius=ft.BorderRadius.all(14),
                ),
                ft.Text(
                    title,
                    size=15,
                    weight=ft.FontWeight.W_700,
                    color=t.TEXT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    message,
                    size=12.5,
                    color=t.MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                *( [action] if action else [] ),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.symmetric(horizontal=28, vertical=48),
        border=ft.Border.all(1, t.BORDER),
        border_radius=ft.BorderRadius.all(14),
        bgcolor=t.SURFACE,
    )


def selectable_chip(
    label: str,
    selected: bool,
    on_click: Callable[[ft.Event], None],
    *,
    icon: str | None = None,
) -> ft.Container:
    """Píldora seleccionable para cambiar de modo o de periodo."""
    controls: list[ft.Control] = []
    color = t.ON_BRAND if selected else t.MUTED
    if icon:
        controls.append(ft.Icon(icon, size=13, color=color))
    controls.append(
        ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=color)
    )
    return ft.Container(
        content=ft.Row(controls, spacing=6, tight=True),
        padding=ft.Padding.symmetric(horizontal=13, vertical=8),
        bgcolor=t.BRAND if selected else t.alpha("#FFFFFF", 0.03),
        border=ft.Border.all(1, t.BRAND if selected else t.BORDER),
        border_radius=ft.BorderRadius.all(999),
        on_click=on_click,
        ink=True,
    )


def set_chip_selected(chip: ft.Container, selected: bool) -> None:
    """Aplica el estado visual a una píldora creada con selectable_chip."""
    chip.bgcolor = t.BRAND if selected else t.alpha("#FFFFFF", 0.03)
    chip.border = ft.Border.all(1, t.BRAND if selected else t.BORDER)
    if isinstance(chip.content, ft.Row):
        for control in chip.content.controls:
            control.color = t.ON_BRAND if selected else t.MUTED


def safe_update(control: ft.Control) -> None:
    """Actualiza un control ignorando los fallos si aún no está montado."""
    try:
        control.update()
    except (AssertionError, RuntimeError, AttributeError):
        pass


def toast(page: ft.Page, message: str, *, kind: str = "ok") -> None:
    """Muestra un aviso flotante en la parte inferior."""
    palette = {
        "ok": (t.BRAND, "check-circle"),
        "info": (t.CYAN, "info"),
        "warn": (t.YELLOW, "warning-amber"),
        "error": (t.DANGER, "error"),
    }
    color, icon_name = palette.get(kind, palette["ok"])
    icon = getattr(ft.Icons, icon_name.upper().replace("-", "_"), ft.Icons.INFO)
    on_color = t.ON_BRAND if kind == "ok" else t.TEXT

    snack = ft.SnackBar(
        content=ft.Row(
            [
                ft.Icon(icon, size=16, color=on_color),
                ft.Text(message, size=12.5, color=on_color, weight=ft.FontWeight.W_600),
            ],
            spacing=9,
            tight=True,
        ),
        bgcolor=color if kind == "ok" else t.SURFACE_ALT,
        duration=3200,
        behavior=ft.SnackBarBehavior.FLOATING,
        margin=ft.Margin.only(bottom=18, left=18, right=18),
        shape=ft.RoundedRectangleBorder(radius=10),
    )
    try:
        page.show_dialog(snack)
    except (AssertionError, RuntimeError, AttributeError):
        pass
