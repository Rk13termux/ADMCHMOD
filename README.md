# ADMCHMOD · Panel de Administración Pro

Aplicación de escritorio en **Flet (Python)** para gestionar `chmodxcode.pro`:
editor de contenido con Plantilla Maestra, generación con IA vía OmniRoute,
biblioteca de publicaciones, analíticas y leads de Supabase, y publicación
automatizada con Git.

Este repositorio es el **espejo** de la carpeta `admin/` del proyecto web
[`LANDGPYTHON`](https://github.com/Rk13termux/LADGPYTHON). Sirve como copia de
seguridad y para versionar el panel por separado.

```
ADMCHMOD/
├── admin/                 # paquete Python (código del panel)
│   ├── app.py             # ventana, pestañas, estado
│   ├── config.py          # .env, Settings, validación
│   ├── branding.py        # Plantilla Maestra
│   ├── content.py         # front matter, validación, guardado
│   ├── omniroute.py       # generación con IA
│   ├── supabase_api.py    # cliente REST
│   ├── git_ops.py         # build + commit + push
│   ├── tabs/              # editor · contenido · analíticas · leads · publicación
│   ├── assets/            # logo.png, icon.png (logo recortado) y logo.ico
│   └── sql/               # esquema y migración de Supabase
└── sync.sh                # sincroniza con el proyecto web
```

## Requisitos

```bash
python3 -m pip install -r admin/requirements.txt
```

`flet`, `flet-desktop`, `httpx`, `python-dotenv`.

## Configuración

Copia el ejemplo y rellena tus valores:

```bash
cp admin/.env.example admin/.env
```

```dotenv
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
CHMODX_GIT_TOKEN=
OMNIROUTE_BASE_URL=http://127.0.0.1:20128/v1
```

> `admin/.env` **no se versiona**: contiene la clave de servicio de Supabase y
> el token de GitHub. Nunca lo subas al repositorio.

## Uso

El panel trabaja sobre un proyecto web (el que contiene `content/`,
`scripts/build.py` y las plantillas). Indica su ruta:

```bash
export CHMODX_PROJECT_ROOT=/ruta/a/LANDINGPYTHON
python3 -m admin --check     # diagnóstico
python3 -m admin             # abre la ventana
python3 -m admin --web       # interfaz en el navegador
```

Sin `CHMODX_PROJECT_ROOT` toma la carpeta padre de `admin/`, que en este
repositorio no contiene el sitio: el editor y la biblioteca necesitan esa ruta.

### Pestañas

| Pestaña | Función |
|---|---|
| **Editor** | Manual, con IA (OmniRoute) o importando un `.md` |
| **Contenido** | Biblioteca: editar, ver en el sitio, eliminar |
| **Analíticas** | Visitas, conversión y rendimiento de los CTA |
| **Leads** | Correos capturados, con exportación a CSV |
| **Publicación** | `build.py` + `git add` + `commit` + `push` |

### Icono en la barra de aplicaciones (Linux)

```bash
python3 -m admin --install-icon
```

Instala el logo en el tema hicolor y un lanzador `com.appveyor.flet.desktop`
para que la barra de tareas muestre el icono del panel.

## Logo e icono

La cabecera usa `admin/assets/icon.png` (el logo recortado, sin el margen
transparente) y `admin/assets/logo.ico` como icono de ventana en Windows.
`logo.png` es el original: si se reemplaza, hay que regenerar los derivados
con el fragmento que aparece en `admin/README.md`, sección «Identidad visual».

Al empaquetar con `flet build`, copia `admin/assets/icon.png` como
`assets/icon.png` en la raíz de compilación: es el icono que toma el paquete.

## Sincronizar este espejo

Cuando cambies el panel en el proyecto web:

```bash
./sync.sh /ruta/a/LANDINGPYTHON/admin
```

Copia sin `.env`, sin caché y sin exportaciones, y publica el cambio.

## Seguridad

- Ninguna credencial está en el código ni en el historial.
- El token de Git se usa con un `credential.helper` efímero: nunca se escribe
  en la URL ni en `.git/config`.
- El panel nunca se conecta a Supabase con la clave de servicio desde el
  navegador; esa clave solo existe en el `.env` local.
