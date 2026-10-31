"""Plantilla Maestra de branding.

Cualquier contenido creado desde el panel pasa por aquí: mismo orden de
secciones, mismo tono, mismos avisos y el mismo cierre con llamado a la
Academia. Así el sitio no se degrada con el tiempo.
"""

from __future__ import annotations

from dataclasses import dataclass


# --------------------------------------------------------------------------- #
# Taxonomía compartida con scripts/build.py
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Category:
    key: str
    label: str
    icon: str
    accent: str
    closing: str


CATEGORIES: dict[str, Category] = {
    "python": Category(
        key="python",
        label="Python",
        icon="code",
        accent="#00E5FF",
        closing=(
            "Copiar un script resuelve una tarea. Entender cada línea te permite "
            "resolver la siguiente. La Academia Python Pro construye esa base paso a paso."
        ),
    ),
    "ciberseguridad": Category(
        key="ciberseguridad",
        label="Ciberseguridad",
        icon="shield",
        accent="#FFD43B",
        closing=(
            "Practicar comandos sueltos no te prepara para una auditoría. En la academia "
            "trabajas alcance, evidencia y reporte con método."
        ),
    ),
    "termux": Category(
        key="termux",
        label="Termux",
        icon="terminal",
        accent="#00E676",
        closing=(
            "Tu Android puede ser un laboratorio completo. En la academia montamos el "
            "entorno, los proyectos y el flujo de trabajo desde cero."
        ),
    ),
    "automatizacion": Category(
        key="automatizacion",
        label="Automatización",
        icon="settings",
        accent="#7DFFC0",
        closing=(
            "Automatizar sin criterio crea deuda técnica. Aprende a diseñar scripts que "
            "puedas mantener, probar y reutilizar durante años."
        ),
    ),
}

CATEGORY_OPTIONS: list[tuple[str, str]] = [
    (key, f"{value.label}") for key, value in CATEGORIES.items()
]

KINDS: dict[str, str] = {
    "repos": "Repositorio",
    "guias": "Guía técnica",
}

KIND_OPTIONS: list[tuple[str, str]] = [(key, label) for key, label in KINDS.items()]

LEVELS: list[str] = ["Principiante", "Intermedio", "Avanzado"]


# --------------------------------------------------------------------------- #
# Bloques de marca
# --------------------------------------------------------------------------- #
def hook_line(summary: str) -> str:
    """Gancho de apertura: una sola frase que resume el valor del contenido."""
    return f"> **En una frase:** {summary.strip()}"


def responsible_use() -> str:
    return (
        "> **Uso responsable:** ejecuta estos comandos solo en equipos propios o en "
        "laboratorios con autorización explícita. El conocimiento técnico no sustituye "
        "el permiso legal."
    )


def commands_section(commands: str) -> str:
    """Sección de comandos con bloque bash listo para copiar."""
    block = commands.strip("\n")
    if block.startswith("```"):
        # El autor ya incluyó el cercado: se respeta tal cual.
        fenced = block
    else:
        fenced = f"```bash\n{block}\n```"
    return (
        "## Comandos de Termux\n\n"
        "Copia y ejecuta en orden. Cada bloque está pensado para un entorno limpio.\n\n"
        f"{fenced}"
    )


# --------------------------------------------------------------------------- #
# Esqueleto editable
# --------------------------------------------------------------------------- #
def master_skeleton(kind: str, category: str) -> str:
    """Estructura base que se inserta en el editor."""
    security_note = (
        "\n> **Uso responsable:** ejecuta estos comandos solo en equipos propios o "
        "en laboratorios con autorización explícita.\n"
        if category == "ciberseguridad"
        else ""
    )

    errors = (
        "## Errores frecuentes\n\n"
        "| Síntoma | Causa probable | Solución |\n"
        "|---|---|---|\n"
        "| `command not found` | Falta una dependencia | Revisa los requisitos |\n"
        "| Permiso denegado | Falta el bit de ejecución | `chmod +x script.sh` |\n"
    )

    if kind == "guias":
        return (
            "## Por qué importa\n\n"
            "Explica el problema real antes de mostrar la solución.\n"
            f"{security_note}\n"
            "## Cómo funciona\n\n"
            "Desglosa el concepto con un ejemplo mínimo y ejecutable.\n\n"
            "## Paso a paso\n\n"
            "### 1. Prepara el entorno\n\n"
            "Describe el punto de partida.\n\n"
            "### 2. Ejecuta\n\n"
            "Muestra el comando y qué debería ocurrir.\n\n"
            f"{errors}"
        )

    return (
        "## Qué vas a construir\n\n"
        "Describe en dos o tres frases qué hace la herramienta y para qué sirve.\n"
        f"{security_note}\n"
        "## Requisitos\n\n"
        "- Python 3.10 o superior.\n"
        "- Un entorno aislado (virtualenv o Termux).\n\n"
        "## El código\n\n"
        "Explica las decisiones importantes antes de pegar el bloque.\n\n"
        "## Cómo ejecutarlo\n\n"
        "Indica el comando exacto y la salida esperada.\n\n"
        f"{errors}"
    )


# --------------------------------------------------------------------------- #
# Ensamblado
# --------------------------------------------------------------------------- #
def compose_body(
    *,
    summary: str,
    body: str,
    category: str,
    commands: str = "",
) -> str:
    """Aplica la Plantilla Maestra al contenido escrito por la persona.

    Reglas:
    - Siempre abre con el gancho de una frase.
    - En ciberseguridad añade el aviso de uso responsable si no está.
    - Añade la sección de comandos solo si hay comandos.

    No añade ningún cierre comercial: de eso se encarga la plantilla de la
    página (bloque ``cta-end``) y las tarjetas de contenido relacionado. Así
    cada artículo termina con una sola llamada a la acción.
    """
    parts: list[str] = [hook_line(summary)]

    clean_body = body.strip()
    if category == "ciberseguridad" and "uso responsable" not in clean_body.lower():
        parts.append(responsible_use())

    if clean_body:
        parts.append(clean_body)

    if commands.strip():
        parts.append(commands_section(commands))

    return "\n\n".join(parts).strip() + "\n"
