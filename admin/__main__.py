"""Punto de entrada del panel.

    python3 -m admin            # abre la aplicación
    python3 -m admin --check    # valida configuración, plantillas y Git
"""

from __future__ import annotations

import argparse
import sys
import types

from . import __version__
from .config import load_settings, mask_secret


def _stub_page() -> types.SimpleNamespace:
    """Página falsa para construir la interfaz sin abrir ventana."""
    return types.SimpleNamespace(
        run_thread=lambda *_a, **_k: None,
        show_dialog=lambda *_a, **_k: None,
        update=lambda *_a, **_k: None,
        clipboard=types.SimpleNamespace(set=lambda *_a, **_k: None),
        fonts=None,
        window=types.SimpleNamespace(),
    )


def check() -> int:
    """Diagnóstico sin interfaz. Devuelve el código de salida."""
    from . import git_ops
    from .app import AdminApp
    from .content import ContentDraft

    print(f"CHMODX · Panel de Administración Pro v{__version__}\n")

    settings = load_settings()
    print("Configuración")
    print(f"  proyecto        {settings.project_root}")
    print(f"  contenido       {'ok' if settings.content_dir.is_dir() else 'FALTA'}")
    print(f"  supabase        {'configurado' if settings.supabase_ready else 'sin configurar'}")
    print(f"  clave de lectura {mask_secret(settings.read_key)}")
    print(f"  .env            {', '.join(str(p) for p in settings.env_files) or 'ninguno'}")
    print(f"  git             {settings.git_remote}/{settings.git_branch}")

    problems = settings.blocking_issues()
    notes = settings.warnings() + settings.supabase_issues()

    print("\nRepositorio")
    repo = git_ops.inspect_repo(settings.project_root, settings.git_remote, settings.git_branch)
    if repo.ok:
        print(f"  rama            {repo.branch}")
        print(f"  modificados     {repo.dirty_files}")
        print(f"  por subir       {repo.ahead}")
        print(f"  último commit   {repo.last_commit}")
    else:
        print(f"  error           {repo.error}")

    print("\nIA (OmniRoute)")
    from .omniroute import OmniRouteClient, OmniRouteConfig

    omni = OmniRouteClient(
        OmniRouteConfig(
            base_url=settings.omniroute_url,
            api_key=settings.omniroute_key,
            model=settings.omniroute_model,
            timeout=3.0,
        )
    )
    ok, detail = omni.health()
    print(f"  endpoint        {settings.omniroute_url}")
    print(f"  modelo          {settings.omniroute_model}")
    print(f"  estado          {'disponible' if ok else 'no disponible'}")
    if not ok:
        notes.append(f"OmniRoute: {detail}")

    from . import desktop

    if desktop.supported():
        print("\nEscritorio")
        print(f"  sesión          {desktop.session()}")
        print(f"  icono           {'instalado' if desktop.is_installed() else 'sin instalar'}")
        if not desktop.is_installed():
            notes.append(
                "Icono del escritorio: ejecuta python3 -m admin --install-icon"
            )

    print("\nPlantilla maestra")
    draft = ContentDraft(
        kind="repos",
        title="Prueba de plantilla maestra",
        summary="Comprobación automática del ensamblado de contenido del panel.",
        category="python",
        body="## Qué vas a construir\n\nTexto de prueba.",
        commands="python3 --version",
        tags="prueba, plantilla",
        stack="Python 3",
    )
    document = draft.document()
    checks = {
        "front matter": document.startswith("---\n"),
        "gancho": "> **En una frase:**" in document,
        "comandos": "```bash" in document,
        "sin cierre duplicado": "## Siguiente paso" not in document,
        "slug": draft.final_slug == "prueba-de-plantilla-maestra",
    }
    for label, ok in checks.items():
        print(f"  {label:<14} {'ok' if ok else 'FALLA'}")

    print("\nInterfaz")
    try:
        app = AdminApp(_stub_page(), settings)
        total = 0
        for tab in app.tabs_list:
            controls = len(tab.view.controls) if hasattr(tab.view, "controls") else 0
            total += controls
            print(f"  {tab.__class__.__name__:<14} {controls} bloques")
        print(f"  total          {total} bloques construidos")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"La interfaz no se pudo construir: {exc}")
        print(f"  error          {exc}")

    if notes:
        print("\nAvisos")
        for note in notes:
            print(f"  · {note}")

    if problems:
        print("\nProblemas")
        for problem in problems:
            print(f"  ✕ {problem}")
        return 1

    print("\nTodo en orden.")
    return 0


def install_icon() -> int:
    """Instala el icono y el lanzador del escritorio."""
    from . import desktop

    print(f"CHMODX · icono del escritorio ({desktop.session()})\n")

    if not desktop.supported():
        print("Solo disponible en Linux.")
        print("En Windows el icono lo carga page.window.icon desde logo.ico.")
        return 1

    settings = load_settings()
    try:
        result = desktop.install(settings.project_root)
    except (OSError, ValueError) as exc:
        print(f"  ✕ {exc}")
        return 1

    icons = result["icons"]
    caches = result["caches"]
    print(f"  lanzador        {result['desktop']}")
    print(f"  iconos          {len(icons)} tamaños en {desktop.icons_dir()}")
    if caches:
        print(f"  cachés          {', '.join(caches)}")
    print("\nListo. Abre CHMODX desde el menú de aplicaciones o vuelve a iniciar")
    print("el panel: la barra de tareas ya mostrará su icono.")
    return 0


def uninstall_icon() -> int:
    """Quita el icono y el lanzador instalados."""
    from . import desktop

    if not desktop.supported():
        print("Solo disponible en Linux.")
        return 1

    if not desktop.is_installed():
        print("No hay nada que quitar: el icono no está instalado.")
        return 0

    removed = desktop.uninstall()
    print(f"CHMODX · icono del escritorio ({desktop.session()})\n")
    print(f"  eliminados      {len(removed)} archivos")
    print("\nHecho. La barra de tareas volverá al icono de Flet.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m admin",
        description="Panel de Administración Pro de chmodxcode.pro",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="valida configuración, plantillas y repositorio sin abrir la ventana",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="sirve la interfaz en el navegador en lugar de abrir una ventana",
    )
    parser.add_argument(
        "--install-icon",
        action="store_true",
        help="instala el icono y el lanzador del escritorio (Linux)",
    )
    parser.add_argument(
        "--uninstall-icon",
        action="store_true",
        help="quita el icono y el lanzador instalados",
    )
    parser.add_argument("--host", default="127.0.0.1", help="host para el modo web")
    parser.add_argument("--port", type=int, default=8560, help="puerto para el modo web")
    args = parser.parse_args(argv)

    if args.check:
        return check()

    if args.install_icon:
        return install_icon()

    if args.uninstall_icon:
        return uninstall_icon()

    from .app import run

    run(web=args.web, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
