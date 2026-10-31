"""Identidad visual del panel: mismos tokens que el sitio público.

Fondo negro, verde fosforescente, cian y amarillo. Tipografías Space Grotesk
para títulos, Inter para texto y Fira Code para código.
"""

from __future__ import annotations

from pathlib import Path

import flet as ft

# --------------------------------------------------------------------------- #
# Tokens de color (idénticos a css/style.css y css/site.css)
# --------------------------------------------------------------------------- #
BG = "#000000"
SURFACE = "#0B0B0B"
SURFACE_ALT = "#111111"
SURFACE_HOVER = "#151515"
BORDER = "#1E1E1E"
BORDER_SOFT = "#161616"

TEXT = "#F5F5F5"
MUTED = "#A1A1A1"
DIM = "#6B6B6B"

BRAND = "#00E676"
BRAND_DARK = "#00A854"
CYAN = "#00E5FF"
YELLOW = "#FFD43B"
DANGER = "#FF4D4D"
TELEGRAM = "#2AABEE"

ON_BRAND = "#00130A"

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"

DISPLAY_FONT = "Space Grotesk"
BODY_FONT = "Inter"
MONO_FONT = "Fira Code"


def register_fonts(page: ft.Page) -> dict[str, str]:
    """Registra las tipografías locales si existen.

    Si no hay archivos en ``admin/assets/fonts`` se usan las del sistema, así
    la app arranca igual en cualquier equipo.
    """
    wanted = {
        DISPLAY_FONT: ("SpaceGrotesk-Bold.ttf", "SpaceGrotesk-SemiBold.ttf"),
        BODY_FONT: ("Inter-Regular.ttf", "Inter-Medium.ttf"),
        MONO_FONT: ("FiraCode-Regular.ttf", "FiraCode-Medium.ttf"),
    }

    registered: dict[str, str] = {}
    for family, candidates in wanted.items():
        for filename in candidates:
            path = FONT_DIR / filename
            if path.is_file():
                registered[family] = str(path)
                break

    if registered:
        page.fonts = {**registered}
    return registered


def body_font() -> str | None:
    return BODY_FONT if (FONT_DIR / "Inter-Regular.ttf").is_file() else None


def mono_font() -> str | None:
    return MONO_FONT if (FONT_DIR / "FiraCode-Regular.ttf").is_file() else None


def display_font() -> str | None:
    return DISPLAY_FONT if (FONT_DIR / "SpaceGrotesk-Bold.ttf").is_file() else None


def build_theme() -> ft.Theme:
    """Tema global oscuro alineado con la web."""
    return ft.Theme(
        use_material3=True,
        font_family=body_font(),
        color_scheme=ft.ColorScheme(
            primary=BRAND,
            on_primary=ON_BRAND,
            primary_container="#0E2A1C",
            on_primary_container=BRAND,
            secondary=CYAN,
            on_secondary="#001418",
            tertiary=YELLOW,
            on_tertiary="#1A1400",
            surface=SURFACE,
            on_surface=TEXT,
            surface_container=SURFACE_ALT,
            surface_container_high=SURFACE_HOVER,
            surface_container_low="#080808",
            on_surface_variant=MUTED,
            outline=BORDER,
            outline_variant=BORDER_SOFT,
            error=DANGER,
            on_error="#1A0000",
            error_container="#2A0A0A",
            on_error_container=DANGER,
        ),
        dialog_theme=ft.DialogTheme(
            bgcolor=SURFACE_ALT,
            barrier_color=alpha("#000000", 0.74),
            shape=ft.RoundedRectangleBorder(radius=16),
            elevation=0,
            title_text_style=ft.TextStyle(
                size=17, weight=ft.FontWeight.W_700, color=TEXT
            ),
            content_text_style=ft.TextStyle(size=13, color=MUTED),
            actions_padding=ft.Padding.only(left=24, right=24, bottom=20, top=4),
        ),
        divider_color=BORDER_SOFT,
        hint_color=DIM,
        splash_color=ft.Colors.with_opacity(0.08, BRAND),
        highlight_color=ft.Colors.with_opacity(0.05, BRAND),
        hover_color=ft.Colors.with_opacity(0.04, BRAND),
    )


def alpha(color: str, opacity: float) -> str:
    """Devuelve un color con transparencia (ARGB hex)."""
    value = color.lstrip("#")
    if len(value) == 8:
        value = value[2:]
    a = max(0, min(255, round(opacity * 255)))
    return f"#{a:02X}{value.upper()}"
