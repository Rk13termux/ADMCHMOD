"""Pestaña 4 · Publicación y automatización de Git."""

from __future__ import annotations

from datetime import datetime

import flet as ft

from .. import git_ops, theme as t, widgets
from ..content import ContentDraft
from ..context import AppContext


class PublishTab:
    """Guarda, construye y empuja el contenido al repositorio."""

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self.running = False
        self.repo: git_ops.RepoState | None = None
        self._build()
        self.view = self._compose()

    def on_mount(self) -> None:
        """Se llama cuando la vista ya está montada en la página."""
        self.refresh_state()

    def sync(self) -> None:
        """Refresca el borrador y el repositorio al entrar en la pestaña."""
        self._render_draft()
        self.refresh_state()

    # ------------------------------------------------------------------ controles
    def _build(self) -> None:
        self.repo_pill_holder = ft.Container(content=widgets.pill("comprobando…", color=t.DIM))
        self.draft_title = ft.Text("Sin contenido seleccionado", size=14,
                                   weight=ft.FontWeight.W_700, color=t.TEXT)
        self.draft_meta = ft.Text("—", size=11.5, color=t.DIM)
        self.draft_path = ft.Text("", size=11.5, color=t.CYAN, font_family=t.mono_font())

        self.run_build = ft.Switch(
            label="Ejecutar build del sitio antes de publicar",
            value=True,
            active_color=t.BRAND,
            label_text_style=ft.TextStyle(size=12, color=t.MUTED),
        )
        self.dry_run = ft.Switch(
            label="Simulación (no hace push)",
            value=False,
            active_color=t.YELLOW,
            label_text_style=ft.TextStyle(size=12, color=t.MUTED),
        )

        self.publish_button = widgets.primary_button(
            "Publicar ahora", ft.Icons.CLOUD_UPLOAD, self._on_publish
        )

        self.state_rows = ft.Column(spacing=8)
        self.log_view = ft.ListView(
            spacing=2,
            auto_scroll=True,
            expand=True,
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        )
        self.log_box = ft.Container(
            content=self.log_view,
            expand=True,
            bgcolor="#050505",
            border=ft.Border.all(1, t.BORDER),
            border_radius=ft.BorderRadius.all(12),
        )
        self.log_hint = ft.Text("Listo.", size=11, color=t.DIM)

    # ------------------------------------------------------------------ layout
    def _compose(self) -> ft.Control:
        header = widgets.panel_header(
            "Publicación y Git",
            "Guarda el Markdown, regenera el sitio y dispara el despliegue de GitHub Actions.",
            icon=ft.Icons.CLOUD_UPLOAD,
            actions=[
                self.repo_pill_holder,
                widgets.icon_button(
                    ft.Icons.REFRESH, lambda _e: self.refresh_state(), tooltip="Revisar repositorio"
                ),
            ],
        )

        draft_card = widgets.card(
            ft.Column(
                [
                    ft.Text("CONTENIDO", size=9.5, weight=ft.FontWeight.W_700, color=t.DIM),
                    self.draft_title,
                    self.draft_meta,
                    self.draft_path,
                ],
                spacing=6,
            )
        )

        options_card = widgets.card(
            ft.Column(
                [
                    ft.Text("OPCIONES", size=9.5, weight=ft.FontWeight.W_700, color=t.DIM),
                    self.run_build,
                    self.dry_run,
                    widgets.divider(),
                    self.publish_button,
                ],
                spacing=14,
            )
        )

        state_card = widgets.card(
            ft.Column(
                [
                    ft.Text("REPOSITORIO", size=9.5, weight=ft.FontWeight.W_700, color=t.DIM),
                    self.state_rows,
                ],
                spacing=12,
            )
        )

        left = ft.Column(
            [draft_card, options_card, state_card],
            spacing=14,
            expand=5,
            scroll=ft.ScrollMode.AUTO,
        )

        console = ft.Column(
            [
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Container(width=8, height=8, bgcolor=t.BRAND,
                                             border_radius=ft.BorderRadius.all(4)),
                                ft.Text("Consola de despliegue", size=12.5,
                                        weight=ft.FontWeight.W_700, color=t.TEXT),
                            ],
                            spacing=8,
                        ),
                        ft.Container(expand=True),
                        self.log_hint,
                        widgets.icon_button(
                            ft.Icons.CONTENT_COPY,
                            self._copy_log,
                            tooltip="Copiar registro",
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.log_box,
            ],
            spacing=10,
            expand=7,
        )

        return ft.Column(
            [
                header,
                ft.Row(
                    [left, console],
                    spacing=16,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=16,
            expand=True,
        )

    # ------------------------------------------------------------------ estado
    def refresh_state(self) -> None:
        self.ctx.page.run_thread(self._load_state)

    def _load_state(self) -> None:
        settings = self.ctx.settings
        self.repo = git_ops.inspect_repo(
            settings.project_root, settings.git_remote, settings.git_branch
        )
        self._render_state()
        self._render_draft()

    def _render_state(self) -> None:
        repo = self.repo
        if repo is None or not repo.ok:
            self.repo_pill_holder.content = widgets.pill("sin repositorio", color=t.DANGER)
            self._safe_update(self.repo_pill_holder)
            self.state_rows.controls = [
                ft.Text(repo.error if repo else "Estado desconocido.", size=12, color=t.DANGER)
            ]
            self._safe_update(self.state_rows)
            return

        pending = repo.pending
        color = t.YELLOW if pending else t.BRAND
        label = "cambios pendientes" if pending else "al día"
        self.repo_pill_holder.content = widgets.pill(label, color=color)
        self._safe_update(self.repo_pill_holder)

        token_ok = bool(self.ctx.settings.git_token)
        rows = [
            self._state_line("Rama", f"{repo.branch} → {repo.remote}/{self.ctx.settings.git_branch}"),
            self._state_line("Archivos modificados", str(repo.dirty_files)),
            self._state_line("Commits por subir", str(repo.ahead)),
            self._state_line("Último commit", repo.last_commit or "—"),
            self._state_line(
                "Token de Git",
                "configurado" if token_ok else "sin configurar · el push puede fallar",
                accent=None if token_ok else t.YELLOW,
            ),
        ]
        self.state_rows.controls = rows
        self._safe_update(self.state_rows)

    def _render_draft(self) -> None:
        draft: ContentDraft | None = self.ctx.pending_draft
        if draft is None:
            self.draft_title.value = "Sin contenido nuevo en esta sesión"
            self.draft_meta.value = (
                "Se publicará lo que haya en el árbol de trabajo (cambios manuales incluidos)."
            )
            self.draft_path.value = ""
        else:
            self.draft_title.value = draft.title or "Sin título"
            self.draft_meta.value = (
                f"{draft.kind_label} · {draft.category_data.label} · "
                f"{draft.final_slug}.md"
            )
            self.draft_path.value = f"content/{draft.folder}/{draft.filename()}"

        for control in (self.draft_title, self.draft_meta, self.draft_path):
            self._safe_update(control)

    @staticmethod
    def _state_line(label: str, value: str, accent: str | None = None) -> ft.Control:
        return ft.Row(
            [
                ft.Text(label, size=11.5, color=t.DIM, width=150),
                ft.Text(
                    value,
                    size=11.5,
                    color=accent or t.MUTED,
                    font_family=t.mono_font(),
                    expand=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=10,
        )

    # ------------------------------------------------------------------ log
    def _log(self, message: str, kind: str = "info") -> None:
        colors = {
            "info": t.MUTED,
            "cmd": t.CYAN,
            "ok": t.BRAND,
            "warn": t.YELLOW,
            "error": t.DANGER,
        }
        prefix = {"cmd": "$ ", "ok": "✓ ", "error": "✕ ", "warn": "! "}.get(kind, "· ")
        stamp = datetime.now().strftime("%H:%M:%S")

        self.log_view.controls.append(
            ft.Text(
                f"{stamp}  {prefix}{message}",
                size=11.5,
                color=colors.get(kind, t.MUTED),
                font_family=t.mono_font(),
                selectable=True,
            )
        )
        self._safe_update(self.log_view)

    async def _copy_log(self, _event: ft.Event) -> None:
        text = "\n".join(
            control.value for control in self.log_view.controls if isinstance(control, ft.Text)
        )
        await self.ctx.page.clipboard.set(text or "Sin registro todavía.")
        self.ctx.toast("Registro copiado.", "info")

    # ------------------------------------------------------------------ publicar
    def _on_publish(self, _event: ft.Event) -> None:
        if self.running:
            return
        self.running = True
        self.publish_button.disabled = True
        self.publish_button.update()

        self.log_hint.value = "Publicando…"
        self.log_hint.color = t.YELLOW
        self._safe_update(self.log_hint)
        self._log("Iniciando publicación", "info")
        self.ctx.page.run_thread(self._run_publish)

    def _run_publish(self) -> None:
        settings = self.ctx.settings
        draft = self.ctx.pending_draft
        message = f"cms: {draft.title}" if draft and draft.title else "cms: actualización de contenido"

        self._log(f"mensaje de commit → {git_ops.sanitize_message(message)}", "cmd")

        success = True
        try:
            for result in git_ops.publish(
                settings.project_root,
                message=message,
                remote=settings.git_remote,
                branch=settings.git_branch,
                build_command=settings.build_command,
                run_build=bool(self.run_build.value),
                dry_run=bool(self.dry_run.value),
                token=settings.git_token,
            ):
                self._log(result.name, "cmd")
                for line in (result.output or "").splitlines():
                    if line.strip():
                        self._log(line.rstrip(), "info")
                self._log(result.summary, "ok" if result.ok else "error")
                if not result.ok:
                    if git_ops.looks_like_auth_error(result.output):
                        self._log(
                            "El remoto rechazó las credenciales. Añade "
                            "CHMODX_GIT_TOKEN a admin/.env (token con permiso "
                            "de repo) o ejecuta: gh auth login",
                            "warn",
                        )
                    success = False
                    break
        except Exception as exc:  # noqa: BLE001 - nunca dejar la UI colgada
            self._log(f"Excepción inesperada: {exc}", "error")
            success = False

        if success:
            self._log("Publicación completada. GitHub Actions desplegará en unos segundos.", "ok")
            self.log_hint.value = "Completado"
            self.log_hint.color = t.BRAND
            self.ctx.toast("Contenido publicado.", "ok")
        else:
            self._log("La publicación se detuvo. Revisa el error anterior.", "error")
            self.log_hint.value = "Con errores"
            self.log_hint.color = t.DANGER
            self.ctx.toast("No se pudo publicar. Revisa la consola.", "error")

        self._safe_update(self.log_hint)
        self.running = False
        self.publish_button.disabled = False
        self._safe_update(self.publish_button)
        self._load_state()

    # ------------------------------------------------------------------ util
    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        try:
            control.update()
        except (AssertionError, RuntimeError):
            pass
