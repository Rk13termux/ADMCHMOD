"""Integración con el escritorio: icono en la barra de aplicaciones.

En Linux el icono que muestra la barra de tareas no lo elige la aplicación:
lo resuelve el compositor a partir del ``app_id`` de la ventana. En Wayland,
KDE y GNOME buscan un archivo ``<app_id>.desktop`` en
``~/.local/share/applications``; en X11 hacen lo mismo con ``WM_CLASS``.

El cliente de escritorio de Flet usa siempre ``com.appveyor.flet``, así que
instalar un lanzador con ese nombre basta para que el panel salga con su
logo en la barra, se abra desde el menú o desde la terminal.

En Windows no hace falta nada de esto: ``page.window.icon`` carga
``logo.ico`` directamente.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import theme as t

# Identificador del cliente de escritorio de Flet (su "application-id").
APP_ID = "com.appveyor.flet"

# Nombre con el que se instala el icono en el tema hicolor.
ICON_NAME = "chmodx-panel"

SIZES = (16, 24, 32, 48, 64, 128, 256, 512)

LAUNCHER_NAME = "CHMODX"


def applications_dir() -> Path:
    return Path.home() / ".local" / "share" / "applications"


def icons_dir() -> Path:
    return Path.home() / ".local" / "share" / "icons" / "hicolor"


def desktop_path() -> Path:
    return applications_dir() / f"{APP_ID}.desktop"


def icon_path(size: int) -> Path:
    return icons_dir() / f"{size}x{size}" / "apps" / f"{ICON_NAME}.png"


def is_installed() -> bool:
    return desktop_path().is_file()


# --------------------------------------------------------------------------- #
# Contenido del lanzador
# --------------------------------------------------------------------------- #
def _exec_quote(value: str) -> str:
    """Comillas según el formato .desktop (solo dobles comillas)."""
    if not any(ch in value for ch in ' \t"\'\\'):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def desktop_entry(python: str, project_root: Path) -> str:
    """Texto del archivo ``.desktop`` que abre el panel."""
    exec_line = f"{_exec_quote(python)} -m admin"
    return "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            f"Name={LAUNCHER_NAME}",
            "GenericName=Panel de Administración",
            "Comment=Panel de Administración Pro de chmodxcode.pro",
            f"Exec={exec_line}",
            f"Path={project_root}",
            f"Icon={ICON_NAME}",
            "Terminal=false",
            "Categories=Development;",
            "Keywords=chmodx;cms;contenido;supabase;",
            "StartupNotify=true",
            f"StartupWMClass={APP_ID}",
            "",
        ]
    )


# --------------------------------------------------------------------------- #
# Instalación
# --------------------------------------------------------------------------- #
def _write_icons() -> list[Path]:
    """Copia el logo en el tema hicolor, con todos los tamaños posibles."""
    source = t.ICON_FILE if t.ICON_FILE.is_file() else t.LOGO_FILE
    if not source.is_file():
        raise FileNotFoundError(
            "No hay logo en admin/assets (se esperaba icon.png o logo.png)."
        )

    written: list[Path] = []
    try:
        from PIL import Image  # noqa: PLC0415  (opcional)
    except ImportError:
        # Sin Pillow se instala el tamaño original; el escritorio lo escala.
        target = icon_path(512)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return [target]

    with Image.open(source) as image:
        original = image.convert("RGBA")
        for size in SIZES:
            target = icon_path(size)
            target.parent.mkdir(parents=True, exist_ok=True)
            resized = original.resize((size, size), Image.LANCZOS)
            resized.save(target)
            written.append(target)
    return written


def _refresh_caches() -> list[str]:
    """Actualiza las cachés del escritorio si las herramientas existen."""
    done: list[str] = []
    commands = [
        ("update-desktop-database", [str(applications_dir())]),
        ("gtk-update-icon-cache", ["-f", "-t", str(icons_dir())]),
    ]
    for tool, args in commands:
        if shutil.which(tool):
            try:
                subprocess.run(
                    [tool, *args],
                    check=False,
                    capture_output=True,
                    timeout=20,
                )
                done.append(tool)
            except (OSError, subprocess.SubprocessError):
                pass
    return done


def install(project_root: Path, python: str | None = None) -> dict[str, object]:
    """Instala el icono y el lanzador. Devuelve un resumen de lo hecho."""
    python = python or sys.executable or "python3"

    icons = _write_icons()

    target = desktop_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(desktop_entry(python, project_root), encoding="utf-8")
    target.chmod(0o755)

    return {
        "desktop": target,
        "icons": icons,
        "caches": _refresh_caches(),
    }


def uninstall() -> list[Path]:
    """Quita el lanzador y los iconos instalados."""
    removed: list[Path] = []

    target = desktop_path()
    if target.is_file():
        target.unlink()
        removed.append(target)

    for size in SIZES:
        path = icon_path(size)
        if path.is_file():
            path.unlink()
            removed.append(path)

    _refresh_caches()
    return removed


def supported() -> bool:
    """La integración solo tiene sentido en Linux."""
    return sys.platform.startswith("linux")


def session() -> str:
    """Tipo de sesión gráfica, para los mensajes."""
    if os.environ.get("WAYLAND_DISPLAY"):
        return "Wayland"
    if os.environ.get("DISPLAY"):
        return "X11"
    return "sin sesión gráfica"
