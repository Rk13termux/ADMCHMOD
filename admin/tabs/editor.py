"""Pestaña 1 · Editor de contenido con Plantilla Maestra."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from .. import branding, theme as t, widgets
from ..content import (
    ContentDraft,
    SaveError,
    existing_files,
    load_document,
    parse_document,
    save_draft,
    slugify,
)
from ..omniroute import (
    LENGTH_WORDS,
    TONE_WORDS,
    OmniRouteClient,
    OmniRouteConfig,
    OmniRouteError,
)
from ..context import AppContext


def _preview_style() -> ft.MarkdownStyleSheet:
    """Estilo oscuro para el Markdown de la vista previa."""
    return ft.MarkdownStyleSheet(
        p_text_style=ft.TextStyle(size=13.5, color=t.MUTED, height=1.55),
        a_text_style=ft.TextStyle(
            size=13.5, color=t.CYAN, decoration=ft.TextDecoration.UNDERLINE
        ),
        em_text_style=ft.TextStyle(size=13.5, italic=True, color=t.MUTED),
        strong_text_style=ft.TextStyle(
            size=13.5, color=t.TEXT, weight=ft.FontWeight.W_700
        ),
        h1_text_style=ft.TextStyle(
            size=20, color=t.TEXT, weight=ft.FontWeight.W_700
        ),
        h2_text_style=ft.TextStyle(
            size=16.5, color=t.TEXT, weight=ft.FontWeight.W_700
        ),
        h3_text_style=ft.TextStyle(
            size=14.5, color=t.TEXT, weight=ft.FontWeight.W_600
        ),
        code_text_style=ft.TextStyle(
            size=12, color=t.BRAND, font_family=t.mono_font()
        ),
        blockquote_text_style=ft.TextStyle(size=13, color=t.MUTED, italic=True),
        blockquote_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        blockquote_decoration=ft.BoxDecoration(
            bgcolor=t.alpha(t.BRAND, 0.06),
            border=ft.Border.only(left=ft.BorderSide(2, t.BRAND)),
            border_radius=ft.BorderRadius.only(top_right=8, bottom_right=8),
        ),
        codeblock_padding=ft.Padding.all(12),
        codeblock_decoration=ft.BoxDecoration(
            bgcolor="#070707",
            border=ft.Border.all(1, t.BORDER),
            border_radius=ft.BorderRadius.all(8),
        ),
        list_bullet_text_style=ft.TextStyle(size=13, color=t.BRAND),
        table_head_text_style=ft.TextStyle(
            size=12, color=t.TEXT, weight=ft.FontWeight.W_700
        ),
        table_body_text_style=ft.TextStyle(size=12, color=t.MUTED),
        table_cells_padding=ft.Padding.symmetric(horizontal=8, vertical=6),
        horizontal_rule_decoration=ft.BoxDecoration(bgcolor=t.BORDER),
    )


def _section_label(text: str) -> ft.Text:
    return ft.Text(text.upper(), size=9.5, weight=ft.FontWeight.W_700, color=t.DIM)


MODES = [
    ("manual", "Manual", ft.Icons.EDIT),
    ("ai", "Con IA", ft.Icons.AUTO_AWESOME),
    ("import", "Importar .md", ft.Icons.UPLOAD_FILE),
]


class EditorTab:
    """Formulario de creación y edición con vista previa en vivo."""

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self._slug_touched = False
        self._build()
        self.view = self._compose()

    # ------------------------------------------------------------------ estado
    def draft(self) -> ContentDraft:
        return ContentDraft(
            kind=self.kind.value or "repos",
            title=self.title.value or "",
            summary=self.summary.value or "",
            category=self.category.value or "python",
            level=self.level.value or "Principiante",
            slug=self.slug.value or "",
            body=self.body.value or "",
            commands=self.commands.value or "",
            tags=self.tags.value or "",
            stack=self.stack.value or "",
            repo_url=self.repo_url.value or "",
            license=self.license.value or "MIT",
            featured=bool(self.featured.value),
            order=int(self.order.value or 99),
        )

    # ------------------------------------------------------------------ controles
    def _build(self) -> None:
        self.kind = widgets.dropdown(
            "Tipo de contenido", branding.KIND_OPTIONS, "repos", self._on_kind_change
        )
        self.category = widgets.dropdown(
            "Categoría", branding.CATEGORY_OPTIONS, "python", self._on_any_change
        )
        self.level = widgets.dropdown(
            "Nivel", [(level, level) for level in branding.LEVELS], "Principiante", None
        )

        self.title = widgets.field(
            "Título",
            hint="Ej.: Escáner de puertos con Python y sockets",
            on_change=self._on_title_change,
        )
        self.summary = widgets.field(
            "Gancho (una frase que resuma el valor)",
            hint="Ej.: Un script para entender qué ocurre en la capa de transporte.",
            multiline=True,
            min_lines=2,
            max_lines=3,
            on_change=self._on_any_change,
        )

        self.slug = widgets.field(
            "Slug (URL)",
            hint="se-genera-desde-el-titulo",
            on_change=self._on_slug_change,
            prefix_icon=ft.Icons.LINK,
        )
        self.tags = widgets.field(
            "Etiquetas",
            hint="redes, sockets, auditoría",
            on_change=self._on_any_change,
        )

        self.stack = widgets.field(
            "Stack", hint="Python 3, Sockets, TCP", on_change=self._on_any_change
        )
        self.repo_url = widgets.field(
            "Repositorio en GitHub",
            hint="https://github.com/usuario/repo (opcional)",
            on_change=self._on_any_change,
        )
        self.license = widgets.field("Licencia", value="MIT")
        self.order = widgets.field("Orden", value="99")
        self.order.width = 88
        self.license.expand = True
        # En un Column, expand empuja en vertical: solo el nivel lo necesita fuera de un Row.
        self.level.expand = False

        self.featured = ft.Switch(
            label="Destacar en el hub",
            value=False,
            active_color=t.BRAND,
            label_text_style=ft.TextStyle(size=12.5, color=t.MUTED),
            on_change=self._on_any_change,
        )

        self.repo_only = ft.Column(
            [self.stack, self.repo_url, self.license], spacing=12, visible=True
        )

        self.body = widgets.field(
            "Contenido Markdown",
            hint="Escribe el cuerpo. La plantilla maestra añade gancho, comandos y cierre.",
            multiline=True,
            min_lines=6,
            max_lines=None,
            on_change=self._on_any_change,
        )
        self.body.expand = True
        self.body.fit_parent_size = True
        self.commands = widgets.field(
            "Comandos de Termux",
            hint="pkg update -y\npkg install -y python git",
            multiline=True,
            min_lines=3,
            max_lines=None,
            on_change=self._on_any_change,
        )
        self.commands.fit_parent_size = True

        self.overwrite = ft.Switch(
            label="Sobrescribir si existe",
            value=False,
            active_color=t.YELLOW,
            label_text_style=ft.TextStyle(size=12, color=t.MUTED),
        )

        self.open_dropdown = widgets.dropdown(
            "Abrir existente",
            self._existing_options(),
            None,
            self._on_open_existing,
            expand=False,
        )
        self.open_dropdown.width = 240

        self.status_text = ft.Text("Listo para escribir.", size=12, color=t.MUTED)

        self.preview_md = ft.Markdown(
            value="",
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            auto_follow_links=False,
            code_theme=ft.MarkdownCodeTheme.ATELIER_CAVE_DARK,
            md_style_sheet=_preview_style(),
        )
        self.preview_meta = ft.Text("—", size=11, color=t.DIM)
        self.preview_path = ft.Text("", size=11.5, color=t.CYAN, font_family=t.mono_font())
        self.live_preview = ft.Switch(
            label="Vista previa en vivo",
            value=True,
            active_color=t.BRAND,
            label_text_style=ft.TextStyle(size=11.5, color=t.MUTED),
            on_change=self._on_any_change,
        )

        # ---------------------------------------------------------- modos
        self.mode = "manual"
        self._generating = False
        self.mode_chips = {
            key: widgets.selectable_chip(
                label,
                key == self.mode,
                lambda _event, k=key: self._set_mode(k),
                icon=icon,
            )
            for key, label, icon in MODES
        }

        # ---------------------------------------------------------- con IA
        self.ai_model = widgets.field(
            "Modelo",
            value=self.ctx.settings.omniroute_model,
            helper="auto deja que OmniRoute elija",
        )
        self.ai_model.expand = False
        self.ai_tone = widgets.dropdown(
            "Tono", [(name, name) for name in TONE_WORDS], "Técnico y directo", None
        )
        self.ai_length = widgets.dropdown(
            "Longitud", [(name, name) for name in LENGTH_WORDS], "Media (~1000 palabras)", None
        )
        self.ai_brief = widgets.field(
            "Idea o encargo",
            hint="Ej.: Un script que organice descargas por tipo de archivo y explique cada paso.",
            multiline=True,
            min_lines=3,
            max_lines=5,
        )
        self.ai_button = widgets.primary_button(
            "Generar borrador", ft.Icons.AUTO_AWESOME, self._on_generate
        )
        self.ai_status = ft.Text("", size=11.5, color=t.DIM)
        self.ai_button.expand = True
        self.ai_panel = ft.Container(
            content=widgets.card(
                ft.Column(
                    [
                        self.ai_brief,
                        self.ai_tone,
                        self.ai_length,
                        self.ai_model,
                        ft.Row([self.ai_button], spacing=0),
                        self.ai_status,
                    ],
                    spacing=10,
                ),
                border_color=t.alpha(t.CYAN, 0.28),
                padding=14,
            ),
            visible=False,
        )

        # ---------------------------------------------------------- importar
        self.file_picker = ft.FilePicker()
        self.import_button = widgets.primary_button(
            "Elegir archivo .md", ft.Icons.UPLOAD_FILE, self._on_pick_file
        )
        self.import_status = ft.Text(
            "Acepta .md con o sin front matter. Si no lo tiene, se toma el primer H1 como título.",
            size=11.5,
            color=t.DIM,
        )
        self.import_button.expand = True
        self.import_panel = ft.Container(
            content=widgets.card(
                ft.Column(
                    [ft.Row([self.import_button], spacing=0), self.import_status],
                    spacing=10,
                ),
                border_color=t.alpha(t.YELLOW, 0.25),
                padding=14,
            ),
            visible=False,
        )

    # ------------------------------------------------------------------ layout
    def _compose(self) -> ft.Control:
        header = widgets.panel_header(
            "Editor de contenido",
            "La Plantilla Maestra se aplica sola al guardar: mismo gancho, mismos avisos, mismo cierre.",
            icon=ft.Icons.EDIT_NOTE,
            actions=[
                self.open_dropdown,
                widgets.ghost_button(
                    "Estructura maestra",
                    ft.Icons.AUTO_AWESOME,
                    self._insert_skeleton,
                    tooltip="Inserta el esqueleto de secciones",
                ),
                widgets.icon_button(
                    ft.Icons.RESTART_ALT, self._reset, tooltip="Limpiar formulario"
                ),
            ],
        )

        # ------------------------------------------------ columna 1 · opciones
        options = ft.Column(
            [
                _section_label("Modo"),
                ft.Row(
                    list(self.mode_chips.values()),
                    spacing=6,
                    run_spacing=6,
                    wrap=True,
                ),
                self.ai_panel,
                self.import_panel,
                widgets.divider(),
                _section_label("Identidad"),
                self.title,
                self.summary,
                self.slug,
                ft.Row([self.kind, self.category], spacing=10),
                self.level,
                self.tags,
                self.repo_only,
                _section_label("Publicación"),
                ft.Row(
                    [self.order, self.license],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.featured,
                self.overwrite,
            ],
            spacing=12,
            width=340,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        # --------------------------------------------- columna 2 · editor .md
        editor_column = ft.Column(
            [
                ft.Row(
                    [
                        _section_label("Contenido Markdown"),
                        ft.Container(expand=True),
                        widgets.badge("Markdown", color=t.CYAN),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.body,
                ft.Row(
                    [
                        _section_label("Comandos de Termux"),
                        ft.Container(expand=True),
                        ft.Text("se envuelven en un bloque bash", size=10.5, color=t.DIM),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(content=self.commands, height=110),
            ],
            spacing=10,
            expand=6,
        )

        # ------------------------------------------- columna 3 · vista previa
        preview_column = ft.Column(
            [
                ft.Row(
                    [
                        _section_label("Vista previa"),
                        ft.Container(expand=True),
                        self.live_preview,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(
                    content=ft.Column(
                        [self.preview_md], scroll=ft.ScrollMode.AUTO, expand=True
                    ),
                    expand=True,
                    padding=ft.Padding.symmetric(horizontal=20, vertical=16),
                    bgcolor=t.SURFACE,
                    border=ft.Border.all(1, t.BORDER),
                    border_radius=ft.BorderRadius.all(14),
                ),
                ft.Row(
                    [self.preview_path, ft.Container(expand=True), self.preview_meta],
                    spacing=10,
                ),
            ],
            spacing=10,
            expand=5,
        )

        action_bar = ft.Container(
            content=ft.Row(
                [
                    self.status_text,
                    ft.Container(expand=True),
                    widgets.ghost_button("Guardar borrador", ft.Icons.SAVE, self._on_save),
                    widgets.primary_button(
                        "Guardar y publicar",
                        ft.Icons.ROCKET_LAUNCH,
                        self._on_save_and_publish,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            bgcolor=t.SURFACE,
            border=ft.Border.all(1, t.BORDER),
            border_radius=ft.BorderRadius.all(12),
        )

        self._refresh_preview(update=False)

        return ft.Column(
            [
                header,
                ft.Row(
                    [options, editor_column, preview_column],
                    spacing=16,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                action_bar,
            ],
            spacing=14,
            expand=True,
        )

    # ------------------------------------------------------------------ helpers
    def _existing_options(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for kind, label in (("repos", "Repo"), ("guias", "Guía")):
            for path in existing_files(self.ctx.settings.project_root, kind):
                options.append((str(path), f"{label} · {path.stem}"))
        return options

    def _on_kind_change(self, _event: ft.Event | None) -> None:
        is_repo = (self.kind.value or "repos") == "repos"
        self.repo_only.visible = is_repo
        self.repo_only.update()
        self._refresh_preview()

    def _on_title_change(self, _event: ft.Event) -> None:
        if not self._slug_touched:
            self.slug.value = slugify(self.title.value or "")
            self.slug.update()
        self._refresh_preview()

    def _on_slug_change(self, _event: ft.Event) -> None:
        self._slug_touched = bool((self.slug.value or "").strip())
        self._refresh_preview()

    def _on_any_change(self, _event: ft.Event) -> None:
        self._refresh_preview()

    def _on_open_existing(self, _event: ft.Event) -> None:
        selected = self.open_dropdown.value
        if not selected:
            return
        path = Path(selected)
        if not path.is_file():
            self.ctx.toast("El archivo ya no existe.", "error")
            return
        try:
            draft = load_document(path)
        except OSError as exc:
            self.ctx.toast(f"No se pudo leer el archivo: {exc}", "error")
            return

        self._fill_form(draft, keep_slug=True, overwrite=True)
        self.ctx.toast(f"Cargado {path.name}", "info")

    def _insert_skeleton(self, _event: ft.Event) -> None:
        skeleton = branding.master_skeleton(
            self.kind.value or "repos", self.category.value or "python"
        )
        current = (self.body.value or "").strip()
        self.body.value = f"{current}\n\n{skeleton}".strip() if current else skeleton
        self.body.update()
        self._refresh_preview()
        self.ctx.toast("Estructura maestra insertada.", "info")

    def _reset(self, _event: ft.Event) -> None:
        self._slug_touched = False
        for control, value in (
            (self.title, ""), (self.summary, ""), (self.slug, ""),
            (self.body, ""), (self.commands, ""), (self.tags, ""),
            (self.stack, ""), (self.repo_url, ""), (self.license, "MIT"),
            (self.order, "99"),
        ):
            control.value = value
            control.update()
        self.featured.value = False
        self.overwrite.value = False
        self.featured.update()
        self.overwrite.update()
        self._refresh_preview()

    # ------------------------------------------------------------------ carga
    def load_path(self, path: Path) -> None:
        """Abre una publicación existente en el formulario."""
        try:
            draft = load_document(path)
        except (OSError, ValueError) as exc:
            self.ctx.toast(f"No se pudo leer el archivo: {exc}", "error")
            return
        self._fill_form(draft, keep_slug=True, overwrite=True)
        self.ctx.toast(f"Editando {path.name}", "info")

    def new_document(self) -> None:
        """Vacía el formulario para empezar una publicación nueva."""
        self._reset(None)  # type: ignore[arg-type]
        self._set_mode("manual")

    # ------------------------------------------------------------------ modos
    def on_mount(self) -> None:
        """Registra el selector de archivos cuando la vista ya está montada."""
        try:
            self.ctx.page.services.append(self.file_picker)
        except (AttributeError, RuntimeError):
            pass

    def _set_mode(self, key: str) -> None:
        self.mode = key
        for name, chip in self.mode_chips.items():
            widgets.set_chip_selected(chip, name == key)
            widgets.safe_update(chip)
        self.ai_panel.visible = key == "ai"
        self.import_panel.visible = key == "import"
        widgets.safe_update(self.ai_panel)
        widgets.safe_update(self.import_panel)

    def _fill_form(self, draft: ContentDraft, *, keep_slug: bool, overwrite: bool) -> None:
        """Vuelca un borrador en el formulario."""
        self.kind.value = draft.kind if draft.kind in branding.KINDS else "repos"
        self.title.value = draft.title
        self.summary.value = draft.summary
        self.category.value = (
            draft.category if draft.category in branding.CATEGORIES else "python"
        )
        self.level.value = (
            draft.level if draft.level in branding.LEVELS else "Principiante"
        )
        self.slug.value = draft.final_slug
        self.body.value = draft.body
        self.commands.value = draft.commands
        self.tags.value = draft.tags
        self.stack.value = draft.stack
        self.repo_url.value = draft.repo_url
        self.license.value = draft.license or "MIT"
        self.featured.value = draft.featured
        self.order.value = str(draft.order)
        self.overwrite.value = overwrite
        self._slug_touched = keep_slug

        for control in (
            self.kind, self.title, self.summary, self.category, self.level,
            self.slug, self.body, self.commands, self.tags, self.stack,
            self.repo_url, self.license, self.featured, self.order, self.overwrite,
        ):
            widgets.safe_update(control)

        self.repo_only.visible = self.kind.value == "repos"
        widgets.safe_update(self.repo_only)
        self._refresh_preview()

    # ------------------------------------------------------------------ con IA
    def _set_ai_status(self, message: str, kind: str = "info") -> None:
        colors = {
            "info": t.DIM,
            "pending": t.CYAN,
            "ok": t.BRAND,
            "warn": t.YELLOW,
            "error": t.DANGER,
        }
        self.ai_status.value = message
        self.ai_status.color = colors.get(kind, t.DIM)
        widgets.safe_update(self.ai_status)

    def _on_generate(self, _event: ft.Event) -> None:
        brief = (self.ai_brief.value or "").strip()
        if len(brief) < 12:
            self._set_ai_status("Escribe al menos una frase con la idea.", "error")
            return
        if self._generating:
            return

        self._generating = True
        self.ai_button.disabled = True
        widgets.safe_update(self.ai_button)
        self._set_ai_status("Generando con OmniRoute… puede tardar unos segundos.", "pending")
        self.ctx.page.run_thread(self._generate_worker, brief)

    def _generate_worker(self, brief: str) -> None:
        settings = self.ctx.settings
        config = OmniRouteConfig(
            base_url=settings.omniroute_url,
            api_key=settings.omniroute_key,
            model=(self.ai_model.value or settings.omniroute_model or "auto").strip(),
        )
        client = OmniRouteClient(config)

        try:
            data = client.generate(
                brief,
                kind_label=branding.KINDS.get(self.kind.value or "repos", "Repositorio"),
                category_label=branding.CATEGORIES.get(
                    self.category.value or "python", branding.CATEGORIES["python"]
                ).label,
                level=self.level.value or "Principiante",
                tone=self.ai_tone.value or "Técnico y directo",
                length=self.ai_length.value or "Media (~1000 palabras)",
            )
        except OmniRouteError as exc:
            self._finish_generation(None, str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - la UI nunca debe colgarse
            self._finish_generation(None, f"Error inesperado: {exc}")
            return

        self._finish_generation(data, None)

    def _finish_generation(self, data: dict | None, error: str | None) -> None:
        self._generating = False
        self.ai_button.disabled = False
        widgets.safe_update(self.ai_button)

        if error or not data:
            self._set_ai_status(error or "OmniRoute no devolvió contenido.", "error")
            self.ctx.toast("No se pudo generar el borrador.", "error")
            return

        draft = ContentDraft(
            kind=self.kind.value or "repos",
            title=data["title"],
            summary=data["summary"],
            category=self.category.value or "python",
            level=self.level.value or "Principiante",
            body=data["body"],
            commands=data["commands"],
            tags=", ".join(data["tags"]),
            stack=", ".join(data["stack"]),
        )
        self._fill_form(draft, keep_slug=False, overwrite=False)

        if data.get("fallback"):
            self._set_ai_status(
                "Respuesta sin JSON válido: se usó el texto completo como cuerpo.", "warn"
            )
        else:
            self._set_ai_status(
                f"Borrador listo ({len(data['body'])} caracteres). Revísalo antes de guardar.",
                "ok",
            )
        self.ctx.toast("Borrador generado.", "ok")

    # ------------------------------------------------------------------ importar
    def _set_import_status(self, message: str, kind: str = "info") -> None:
        colors = {"info": t.DIM, "ok": t.BRAND, "error": t.DANGER}
        self.import_status.value = message
        self.import_status.color = colors.get(kind, t.DIM)
        widgets.safe_update(self.import_status)

    async def _on_pick_file(self, _event: ft.Event) -> None:
        try:
            files = await self.file_picker.pick_files(
                dialog_title="Elegir un archivo Markdown",
                allowed_extensions=["md", "markdown", "txt"],
                allow_multiple=False,
                with_data=True,
            )
        except Exception as exc:  # noqa: BLE001
            self._set_import_status(f"No se pudo abrir el selector: {exc}", "error")
            return

        if not files:
            return

        chosen = files[0]
        try:
            if chosen.bytes:
                text = chosen.bytes.decode("utf-8", errors="replace")
            elif chosen.path:
                text = Path(chosen.path).read_text(encoding="utf-8", errors="replace")
            else:
                raise OSError("el archivo llegó vacío")
        except (OSError, UnicodeDecodeError) as exc:
            self._set_import_status(f"No se pudo leer el archivo: {exc}", "error")
            return

        try:
            draft = parse_document(text, chosen.name or "documento.md")
        except Exception as exc:  # noqa: BLE001
            self._set_import_status(f"Markdown no válido: {exc}", "error")
            return

        self._fill_form(draft, keep_slug=True, overwrite=True)
        self._set_import_status(
            f"Importado {chosen.name} · {len(text)} caracteres", "ok"
        )
        self.ctx.toast(f"Importado {chosen.name}", "ok")

    # ------------------------------------------------------------------ preview
    def _refresh_preview(self, update: bool = True) -> None:
        draft = self.draft()

        if self.live_preview.value:
            if not draft.title.strip() and not draft.body.strip():
                self.preview_md.value = (
                    "_Escribe el título y el contenido para ver aquí la vista previa._"
                )
            else:
                self.preview_md.value = draft.body_markdown()
            stats = draft.stats()
            self.preview_meta.value = (
                f"{stats['palabras']} palabras · {stats['lectura']} · "
                f"{stats['secciones']} secciones"
            )
            self.preview_path.value = draft.public_path if draft.final_slug else "—"

        self._refresh_issues(update=update)

        if not update:
            return
        for control in (self.preview_md, self.preview_meta, self.preview_path):
            try:
                control.update()
            except (AssertionError, RuntimeError):
                pass

    def _refresh_issues(self, update: bool = True) -> None:
        draft = self.draft()
        issues = draft.validate(
            self.ctx.settings.project_root,
            allow_overwrite=bool(self.overwrite.value),
        )
        errors = [msg for level, msg in issues if level == "error"]
        warns = [msg for level, msg in issues if level == "warn"]

        if errors:
            self.status_text.value = f"{len(errors)} error(es) por resolver · {errors[0]}"
            self.status_text.color = t.DANGER
        elif warns:
            self.status_text.value = f"Listo con {len(warns)} aviso(s): {warns[0]}"
            self.status_text.color = t.YELLOW
        else:
            self.status_text.value = "Todo correcto · listo para guardar"
            self.status_text.color = t.BRAND

        if update:
            try:
                self.status_text.update()
            except (AssertionError, RuntimeError):
                pass

    # ------------------------------------------------------------------ acciones
    def _on_save(self, _event: ft.Event) -> None:
        self._save(notify=True)

    def _on_save_and_publish(self, _event: ft.Event) -> None:
        path = self._save(notify=True)
        if path is None:
            return
        self.ctx.request_publish(self.draft())

    def _save(self, *, notify: bool) -> Path | None:
        draft = self.draft()
        try:
            path = save_draft(
                draft,
                self.ctx.settings.project_root,
                allow_overwrite=bool(self.overwrite.value),
            )
        except SaveError as exc:
            if notify:
                self.ctx.toast(str(exc), "error")
            return None
        except OSError as exc:
            if notify:
                self.ctx.toast(f"No se pudo escribir el archivo: {exc}", "error")
            return None

        self.ctx.saved_path = path
        self.open_dropdown.options = [
            ft.DropdownOption(key=key, text=text) for key, text in self._existing_options()
        ]
        widgets.safe_update(self.open_dropdown)
        self._refresh_issues()

        if notify:
            self.ctx.toast(f"Guardado en content/{draft.folder}/{path.name}", "ok")
        return path
