"""Configuración de la aplicación y carga segura de variables de entorno.

Las credenciales de Supabase nunca se escriben en el código: se leen de un
archivo ``.env`` local (excluido de Git) o del entorno del sistema.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ADMIN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ADMIN_DIR.parent

# Archivos de entorno, en orden de prioridad. El primero que exista se carga.
ENV_FILES = (ADMIN_DIR / ".env", PROJECT_ROOT / ".env")

MISSING = "(sin configurar)"


def _load_env_files() -> list[Path]:
    """Carga los .env disponibles sin sobrescribir variables ya definidas."""
    loaded: list[Path] = []
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dependencia opcional
        return loaded

    for candidate in ENV_FILES:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            loaded.append(candidate)
    return loaded


def mask_secret(value: str, visible: int = 4) -> str:
    """Devuelve una versión enmascarada de una clave para mostrarla en la UI."""
    value = (value or "").strip()
    if not value:
        return MISSING
    if len(value) <= visible * 2:
        return "•" * len(value)
    return f"{value[:visible]}…{value[-visible:]}"


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable de la sesión."""

    supabase_url: str = ""
    anon_key: str = ""
    service_key: str = ""
    project_root: Path = PROJECT_ROOT
    site_url: str = "https://chmodxcode.pro"
    git_remote: str = "origin"
    git_branch: str = "main"
    git_token: str = ""
    build_command: str = "python3 scripts/build.py"
    omniroute_url: str = "http://127.0.0.1:20128/v1"
    omniroute_key: str = ""
    omniroute_model: str = "auto"
    env_files: tuple[Path, ...] = ()

    # ------------------------------------------------------------------ estado
    @property
    def supabase_ready(self) -> bool:
        return bool(self.supabase_url and (self.service_key or self.anon_key))

    @property
    def read_key(self) -> str:
        """Clave usada para leer. El service key manda si está disponible."""
        return self.service_key or self.anon_key

    @property
    def uses_service_key(self) -> bool:
        return bool(self.service_key)

    @property
    def content_dir(self) -> Path:
        return self.project_root / "content"

    @property
    def exports_dir(self) -> Path:
        return ADMIN_DIR / "exports"

    # ------------------------------------------------------------------ avisos
    def blocking_issues(self) -> list[str]:
        """Problemas que impiden usar el panel completo."""
        problems: list[str] = []
        if not self.project_root.is_dir():
            problems.append(f"No existe la carpeta del proyecto: {self.project_root}")
        elif not (self.project_root / "content").is_dir():
            problems.append(
                f"No se encontró la carpeta de contenido en {self.project_root}/content."
            )
        return problems

    def supabase_issues(self) -> list[str]:
        """Problemas que solo afectan a las pestañas de datos."""
        problems: list[str] = []
        if not self.supabase_url:
            problems.append("Falta SUPABASE_URL en el entorno.")
        elif not self.supabase_url.startswith("https://"):
            problems.append("SUPABASE_URL debería empezar por https://")
        if not self.anon_key and not self.service_key:
            problems.append("Falta SUPABASE_ANON_KEY (o SUPABASE_SERVICE_KEY).")
        return problems

    def issues(self) -> list[str]:
        """Todos los problemas, juntos."""
        return self.blocking_issues() + self.supabase_issues()

    def warnings(self) -> list[str]:
        notes: list[str] = []
        if not self.service_key:
            notes.append(
                "Sin SUPABASE_SERVICE_KEY: las lecturas usan la anon key y pueden "
                "quedar bloqueadas por RLS."
            )
        if not self.env_files:
            notes.append("No se encontró ningún archivo .env; usando variables del sistema.")
        return notes


def load_settings() -> Settings:
    """Construye la configuración a partir del entorno."""
    loaded = _load_env_files()

    root = os.environ.get("CHMODX_PROJECT_ROOT", "").strip()
    project_root = Path(root).expanduser().resolve() if root else PROJECT_ROOT

    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")

    return Settings(
        supabase_url=url,
        anon_key=os.environ.get("SUPABASE_ANON_KEY", "").strip(),
        service_key=os.environ.get("SUPABASE_SERVICE_KEY", "").strip(),
        project_root=project_root,
        site_url=os.environ.get("CHMODX_SITE_URL", "https://chmodxcode.pro").strip().rstrip("/"),
        git_remote=os.environ.get("CHMODX_GIT_REMOTE", "origin").strip() or "origin",
        git_branch=os.environ.get("CHMODX_GIT_BRANCH", "main").strip() or "main",
        git_token=(
            os.environ.get("CHMODX_GIT_TOKEN")
            or os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GH_TOKEN")
            or ""
        ).strip(),
        build_command=os.environ.get(
            "CHMODX_BUILD_COMMAND", "python3 scripts/build.py"
        ).strip(),
        omniroute_url=os.environ.get(
            "OMNIROUTE_BASE_URL", "http://127.0.0.1:20128/v1"
        ).strip()
        or "http://127.0.0.1:20128/v1",
        omniroute_key=os.environ.get("OMNIROUTE_API_KEY", "").strip(),
        omniroute_model=os.environ.get("OMNIROUTE_MODEL", "auto").strip() or "auto",
        env_files=tuple(loaded),
    )
