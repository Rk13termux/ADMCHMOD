"""Operaciones de Git y build mediante subprocess.

Reglas de seguridad:
- Nunca se usa ``shell=True``.
- Los argumentos van como lista, no como cadena interpolada.
- El mensaje de commit se sanea para que no se interprete como opción.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    """Error de entorno Git (no de un comando concreto)."""


@dataclass(frozen=True)
class StepResult:
    name: str
    ok: bool
    code: int
    output: str
    seconds: float

    @property
    def summary(self) -> str:
        state = "ok" if self.ok else f"error {self.code}"
        return f"{self.name} · {state} · {self.seconds:.1f}s"


def sanitize_message(message: str, fallback: str = "cms: actualización de contenido") -> str:
    """Limpia el mensaje de commit: una línea, sin caracteres de control."""
    clean = " ".join((message or "").split())
    clean = re.sub(r"[\x00-\x1f]", "", clean).strip()
    if not clean or clean.startswith("-"):
        return fallback
    return clean[:120]


def run_command(
    args: list[str],
    cwd: Path,
    *,
    name: str | None = None,
    timeout: int = 180,
    extra_env: dict[str, str] | None = None,
) -> StepResult:
    """Ejecuta un comando y devuelve su resultado sin lanzar excepciones."""
    label = name or " ".join(args[:3])
    started = time.perf_counter()

    # GIT_TERMINAL_PROMPT=0 hace que git falle al instante si no hay
    # credenciales, en lugar de quedarse esperando una contraseña.
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat"}
    if extra_env:
        env.update(extra_env)

    try:
        completed = subprocess.run(  # noqa: S603 - args es una lista, sin shell
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        elapsed = time.perf_counter() - started
        output = (completed.stdout or "") + (completed.stderr or "")
        return StepResult(
            name=label,
            ok=completed.returncode == 0,
            code=completed.returncode,
            output=output.strip(),
            seconds=elapsed,
        )
    except FileNotFoundError as exc:
        elapsed = time.perf_counter() - started
        return StepResult(label, False, 127, f"No se encontró el comando: {exc}", elapsed)
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - started
        return StepResult(label, False, 124, f"Tiempo agotado ({timeout}s).", elapsed)
    except OSError as exc:  # pragma: no cover - permisos, disco
        elapsed = time.perf_counter() - started
        return StepResult(label, False, 1, f"Error del sistema: {exc}", elapsed)


# --------------------------------------------------------------------------- #
# Estado del repositorio
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RepoState:
    ok: bool
    branch: str = ""
    remote: str = ""
    dirty_files: int = 0
    ahead: int = 0
    behind: int = 0
    last_commit: str = ""
    error: str = ""

    @property
    def pending(self) -> bool:
        return self.dirty_files > 0 or self.ahead > 0


def inspect_repo(root: Path, remote: str = "origin", branch: str = "main") -> RepoState:
    """Comprueba que ``root`` sea un repo Git y resume su estado."""
    if not (root / ".git").exists():
        return RepoState(ok=False, error=f"{root} no es un repositorio Git.")

    inside = run_command(["git", "rev-parse", "--is-inside-work-tree"], root, name="git rev-parse")
    if not inside.ok:
        return RepoState(ok=False, error=inside.output or "Git no disponible.")

    current = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], root, name="git branch")
    current_branch = current.output.strip() if current.ok else branch

    status = run_command(["git", "status", "--porcelain"], root, name="git status")
    dirty = len([line for line in status.output.splitlines() if line.strip()])

    ahead = behind = 0
    tracking = run_command(
        ["git", "rev-list", "--left-right", "--count", f"{remote}/{branch}...HEAD"],
        root,
        name="git rev-list",
    )
    if tracking.ok and tracking.output:
        parts = tracking.output.split()
        if len(parts) == 2:
            behind, ahead = int(parts[0]), int(parts[1])

    last = run_command(["git", "log", "-1", "--pretty=%h %s"], root, name="git log")
    last_commit = last.output.strip() if last.ok else ""

    return RepoState(
        ok=True,
        branch=current_branch,
        remote=remote,
        dirty_files=dirty,
        ahead=ahead,
        behind=behind,
        last_commit=last_commit,
    )


# --------------------------------------------------------------------------- #
# Publicación
# --------------------------------------------------------------------------- #
def _split_build(command: str) -> list[str]:
    """Convierte el comando de build en una lista de argumentos."""
    try:
        return shlex.split(command)
    except ValueError:
        return []


def push_command(remote: str, branch: str, token: str = "") -> tuple[list[str], dict[str, str]]:
    """Construye el comando de push y el entorno necesario.

    Con token se inyecta un credential helper efímero: el valor viaja por
    variable de entorno, nunca en la URL ni en los argumentos del proceso.
    """
    args = ["git"]
    env: dict[str, str] = {}

    if token:
        args += [
            "-c",
            "credential.helper=",
            "-c",
            'credential.helper=!f() { echo "username=x-access-token"; '
            'echo "password=$GIT_TOKEN"; }; f',
        ]
        env["GIT_TOKEN"] = token

    args += ["push", remote, branch]
    return args, env


AUTH_ERROR_HINTS = (
    "invalid username or token",
    "authentication failed",
    "could not read username",
    "permission denied (publickey)",
    "support for password authentication",
    "terminal prompts disabled",
)


def looks_like_auth_error(output: str) -> bool:
    text = (output or "").lower()
    return any(hint in text for hint in AUTH_ERROR_HINTS)


def publish(
    root: Path,
    *,
    message: str,
    remote: str = "origin",
    branch: str = "main",
    build_command: str = "python3 scripts/build.py",
    run_build: bool = True,
    dry_run: bool = False,
    token: str = "",
) -> Iterator[StepResult]:
    """Genera el sitio, hace commit y empuja. Cede un resultado por paso."""
    commit_message = sanitize_message(message)

    if run_build:
        args = _split_build(build_command)
        if not args:
            yield StepResult("build", False, 2, "Comando de build vacío o inválido.", 0.0)
            return
        build = run_command(args, root, name="build del sitio", timeout=180)
        yield build
        # El build valida el contenido: si falla, no se publica nada.
        if not build.ok:
            return

    yield run_command(["git", "add", "-A"], root, name="git add", timeout=60)

    commit = run_command(
        ["git", "commit", "-m", commit_message],
        root,
        name="git commit",
        timeout=60,
    )
    if not commit.ok and ("nothing to commit" in commit.output.lower()
                          or "nada que confirmar" in commit.output.lower()
                          or "no hay cambios" in commit.output.lower()):
        commit = StepResult(
            name="git commit",
            ok=True,
            code=0,
            output="Sin cambios nuevos que confirmar.",
            seconds=commit.seconds,
        )
    yield commit

    if dry_run:
        yield StepResult(
            name="git push",
            ok=True,
            code=0,
            output="Simulación: no se envió nada al remoto.",
            seconds=0.0,
        )
        return

    args, env = push_command(remote, branch, token)
    yield run_command(args, root, name="git push", timeout=180, extra_env=env)
