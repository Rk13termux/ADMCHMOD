"""Modelo de contenido: borrador, front matter, validación y guardado.

El formato de salida es el que consume ``scripts/build.py``: Markdown con
front matter simple (clave: valor, listas entre corchetes).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import branding


# --------------------------------------------------------------------------- #
# Utilidades de texto
# --------------------------------------------------------------------------- #
def slugify(text: str, max_length: int = 70) -> str:
    """Convierte un título en un slug estable, sin acentos ni símbolos."""
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    ascii_text = re.sub(r"-{2,}", "-", ascii_text).strip("-")
    if len(ascii_text) > max_length:
        ascii_text = ascii_text[:max_length].rstrip("-")
    return ascii_text


def _quote(value: str) -> str:
    """Entrecomilla un valor para el front matter que lee el generador."""
    clean = " ".join(str(value).split())
    if '"' not in clean:
        return f'"{clean}"'
    if "'" not in clean:
        return f"'{clean}'"
    return '"' + clean.replace('"', "'") + '"'


def _quote_list(values: list[str]) -> str:
    items = [f"'{v.strip()}'" if '"' in v else f'"{v.strip()}"' for v in values if v.strip()]
    return "[" + ", ".join(items) + "]"


def parse_csv(value: str) -> list[str]:
    """Convierte 'a, b, c' en ['a', 'b', 'c'] sin duplicados."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in re.split(r"[,\n]", value or ""):
        item = raw.strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


def reading_minutes(text: str) -> int:
    return max(3, round(word_count(text) / 200))


# --------------------------------------------------------------------------- #
# Borrador
# --------------------------------------------------------------------------- #
@dataclass
class ContentDraft:
    """Todo lo que el editor necesita para generar un archivo publicable."""

    kind: str = "repos"
    title: str = ""
    summary: str = ""
    category: str = "python"
    level: str = "Principiante"
    slug: str = ""
    body: str = ""
    commands: str = ""
    tags: str = ""
    stack: str = ""
    repo_url: str = ""
    license: str = "MIT"
    featured: bool = False
    order: int = 99
    updated: str = field(default_factory=lambda: date.today().isoformat())

    # ------------------------------------------------------------------ derivados
    @property
    def final_slug(self) -> str:
        return slugify(self.slug or self.title)

    @property
    def tag_list(self) -> list[str]:
        return parse_csv(self.tags)

    @property
    def stack_list(self) -> list[str]:
        return parse_csv(self.stack)

    @property
    def category_data(self) -> branding.Category:
        return branding.CATEGORIES.get(self.category, branding.CATEGORIES["python"])

    @property
    def kind_label(self) -> str:
        return branding.KINDS.get(self.kind, "Contenido")

    @property
    def folder(self) -> str:
        return "repos" if self.kind == "repos" else "guias"

    @property
    def public_path(self) -> str:
        base = "repositorios" if self.kind == "repos" else "guias"
        return f"/{base}/{self.final_slug}/"

    # ------------------------------------------------------------------ salida
    def front_matter(self) -> str:
        lines: list[str] = ["---"]
        lines.append(f"title: {_quote(self.title)}")
        lines.append(f"slug: {_quote(self.final_slug)}")
        lines.append(f"summary: {_quote(self.summary)}")
        lines.append(f"category: {_quote(self.category)}")

        if self.kind == "guias":
            lines.append(f"level: {_quote(self.level)}")
            lines.append(f"reading: {reading_minutes(self.body)}")
        else:
            lines.append(f"difficulty: {_quote(self.level)}")
            lines.append(f"stack: {_quote_list(self.stack_list)}")
            lines.append(f"repo: {_quote(self.repo_url)}")
            lines.append(f"license: {_quote(self.license or 'MIT')}")
            lines.append(f"featured: {'true' if self.featured else 'false'}")
            lines.append(f"order: {int(self.order)}")

        lines.append(f"tags: {_quote_list(self.tag_list)}")
        lines.append(f"updated: {_quote(self.updated)}")
        lines.append("---")
        return "\n".join(lines)

    def body_markdown(self) -> str:
        return branding.compose_body(
            summary=self.summary,
            body=self.body,
            category=self.category,
            commands=self.commands,
        )

    def document(self) -> str:
        """Documento completo listo para escribir en disco."""
        return f"{self.front_matter()}\n\n{self.body_markdown()}"

    def filename(self) -> str:
        return f"{self.final_slug}.md"

    def target_path(self, project_root: Path) -> Path:
        return project_root / "content" / self.folder / self.filename()

    # ------------------------------------------------------------------ validación
    def validate(self, project_root: Path | None = None, *, allow_overwrite: bool = False) -> list[tuple[str, str]]:
        """Devuelve [(nivel, mensaje)] con nivel 'error' o 'warn'."""
        issues: list[tuple[str, str]] = []

        title = self.title.strip()
        if not title:
            issues.append(("error", "El título es obligatorio."))
        elif len(title) < 8:
            issues.append(("error", "El título necesita al menos 8 caracteres."))
        elif len(title) > 120:
            issues.append(("warn", "El título supera los 120 caracteres: se recortará en las tarjetas."))

        summary = self.summary.strip()
        if not summary:
            issues.append(("error", "El gancho es obligatorio: es la frase que vende el contenido."))
        elif len(summary) < 30:
            issues.append(("warn", "El gancho es muy corto (menos de 30 caracteres)."))
        elif len(summary) > 220:
            issues.append(("warn", "El gancho supera los 220 caracteres."))

        if self.category not in branding.CATEGORIES:
            issues.append(("error", "Categoría desconocida."))

        if self.kind not in branding.KINDS:
            issues.append(("error", "Tipo de contenido desconocido."))

        slug = self.final_slug
        if not slug:
            issues.append(("error", "No se pudo generar el slug a partir del título."))
        elif len(slug) < 3:
            issues.append(("error", "El slug es demasiado corto."))
        elif slug != self.slug.strip() and self.slug.strip():
            issues.append(("warn", "El slug tenía caracteres no válidos y se normalizó."))

        body = self.body.strip()
        if not body:
            issues.append(("error", "El contenido está vacío."))
        elif len(body) < 200:
            issues.append(("warn", "El contenido tiene menos de 200 caracteres."))

        if "```" in self.commands and not self.commands.strip().startswith("```"):
            issues.append(("warn", "Los comandos contienen ``` sueltos; revisa el cercado."))

        if self.kind == "repos" and not self.stack_list:
            issues.append(("warn", "Sin stack declarado: la ficha se verá incompleta."))
        if not self.tag_list:
            issues.append(("warn", "Sin etiquetas: el buscador del sitio perderá precisión."))

        if project_root is not None and slug and not allow_overwrite:
            target = self.target_path(project_root)
            if target.exists():
                issues.append(("error", f"Ya existe {target.name}. Cambia el slug o marca 'sobrescribir'."))

        return issues

    @property
    def has_errors(self) -> bool:
        return any(level == "error" for level, _ in self.validate())

    def stats(self) -> dict[str, int | str]:
        words = word_count(self.body)
        return {
            "palabras": words,
            "lectura": f"{reading_minutes(self.body)} min",
            "caracteres": len(self.body),
            "secciones": self.body.count("\n## "),
        }


# --------------------------------------------------------------------------- #
# Guardado
# --------------------------------------------------------------------------- #
class SaveError(RuntimeError):
    """Error controlado al escribir el archivo en el proyecto."""


def save_draft(
    draft: ContentDraft,
    project_root: Path,
    *,
    allow_overwrite: bool = False,
) -> Path:
    """Escribe el Markdown en ``content/repos`` o ``content/guias``."""
    errors = [msg for level, msg in draft.validate(project_root, allow_overwrite=allow_overwrite) if level == "error"]
    if errors:
        raise SaveError("; ".join(errors))

    target = draft.target_path(project_root)
    if target.exists() and not allow_overwrite:
        raise SaveError(f"{target.name} ya existe. Activa 'sobrescribir' para reemplazarlo.")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(draft.document(), encoding="utf-8")
    return target


def existing_files(project_root: Path, kind: str) -> list[Path]:
    folder = project_root / "content" / ("repos" if kind == "repos" else "guias")
    if not folder.is_dir():
        return []
    return sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


# --------------------------------------------------------------------------- #
# Lectura de contenido existente
# --------------------------------------------------------------------------- #
def _unquote(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _parse_list(raw: str) -> list[str]:
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    items: list[str] = []
    current: list[str] = []
    quote = ""
    for char in inner:
        if quote:
            if char == quote:
                quote = ""
            else:
                current.append(char)
        elif char in "\"'":
            quote = char
        elif char == ",":
            items.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    items.append("".join(current).strip())
    return [item for item in items if item]


def split_front_matter(text: str) -> tuple[dict[str, object], str]:
    """Separa el front matter simple del cuerpo Markdown."""
    if not text.startswith("---"):
        return {}, text.strip()

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()

    meta: dict[str, object] = {}
    for line in parts[1].strip().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = _parse_list(value)
        elif value.lower() in {"true", "false"}:
            meta[key] = value.lower() == "true"
        elif re.fullmatch(r"-?\d+", value):
            meta[key] = int(value)
        else:
            meta[key] = _unquote(value)

    return meta, parts[2].strip()


HOOK_PREFIX = "> **En una frase:**"


def parse_document(text: str, filename: str = "documento.md", *, kind: str | None = None) -> ContentDraft:
    """Reconstruye un borrador a partir de un Markdown, con o sin front matter."""
    meta, body = split_front_matter(text)

    if body.startswith(HOOK_PREFIX):
        body = body[len(HOOK_PREFIX):].lstrip()

    if not meta:
        # Markdown suelto: el primer H1 hace de título.
        lines = body.splitlines()
        title = ""
        for index, line in enumerate(lines):
            if line.startswith("# "):
                title = line[2:].strip()
                body = "\n".join(lines[:index] + lines[index + 1:]).strip()
                break
        if not title:
            stem = Path(filename).stem.replace("-", " ").replace("_", " ").strip()
            title = stem[:1].upper() + stem[1:] if stem else "Sin título"
        return ContentDraft(
            kind=kind or "repos",
            title=title,
            summary="",
            category="python",
            level="Principiante",
            slug=slugify(title),
            body=body,
        )

    tags = meta.get("tags") or []
    stack = meta.get("stack") or []
    detected_kind = kind or ("guias" if "level" in meta else "repos")

    return ContentDraft(
        kind=detected_kind,
        title=str(meta.get("title") or Path(filename).stem),
        summary=str(meta.get("summary") or ""),
        category=str(meta.get("category") or "python"),
        level=str(meta.get("level") or meta.get("difficulty") or "Principiante"),
        slug=str(meta.get("slug") or slugify(str(meta.get("title") or Path(filename).stem))),
        body=body,
        tags=", ".join(str(tag) for tag in tags) if isinstance(tags, list) else str(tags),
        stack=", ".join(str(item) for item in stack) if isinstance(stack, list) else str(stack),
        repo_url=str(meta.get("repo") or ""),
        license=str(meta.get("license") or "MIT"),
        featured=bool(meta.get("featured") or False),
        order=int(meta.get("order") or 99),
        updated=str(meta.get("updated") or date.today().isoformat()),
    )


def load_document(path: Path) -> ContentDraft:
    """Reconstruye un borrador a partir de un archivo del proyecto."""
    kind = "repos" if path.parent.name == "repos" else "guias"
    return parse_document(path.read_text(encoding="utf-8"), path.name, kind=kind)
