# Panel de Administración Pro · CHMODX

Aplicación de escritorio en **Flet (Python)** para gestionar `chmodxcode.pro`:
CMS con Plantilla Maestra, analíticas de Supabase, leads y publicación
automatizada por Git.

Interfaz oscura tipo terminal, con los mismos colores del sitio
(`#00e676`, `#00e5ff`, `#ffd43b`) y cinco pestañas:

| Pestaña | Qué hace |
|---|---|
| **Editor** | Crea repositorios y guías aplicando la Plantilla Maestra de branding, con vista previa en vivo. |
| **Contenido** | Lista todo lo publicado; permite editarlo, verlo en el sitio o eliminarlo. |
| **Analíticas** | Lee `page_views` de Supabase y muestra visitas, únicos, conversión, serie diaria y ranking. |
| **Leads** | Lista los correos capturados, con búsqueda y exportación a CSV. |
| **Publicación** | Guarda, ejecuta el build del sitio, hace commit y empuja a GitHub. |

---

## 1. Instalación

```bash
cd /ruta/a/LANDINGPYTHON
python3 -m pip install -r admin/requirements.txt
```

Dependencias: `flet`, `flet-desktop`, `httpx`, `python-dotenv`. No hay Node,
ni bundler, ni base de datos local.

Comprueba que todo está en su sitio **sin abrir la ventana**:

```bash
python3 -m admin --check
```

Salida esperada:

```
Configuración
  proyecto        /ruta/a/LANDINGPYTHON
  contenido       ok
  supabase        configurado
  ...
Todo en orden.
```

---

## 2. Variables de entorno

Copia el ejemplo y rellena los valores:

```bash
cp admin/.env.example admin/.env
```

```dotenv
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
```

`admin/.env` está excluido de Git. La app nunca escribe las claves en el
código ni en los registros; en la barra inferior solo muestra una versión
enmascarada (`abcd…wxyz`).

### Qué clave usa cada cosa

| Clave | Uso | Riesgo |
|---|---|---|
| `SUPABASE_ANON_KEY` | Inserciones desde el sitio público | Bajo: RLS limita a `insert` |
| `SUPABASE_SERVICE_KEY` | Lectura de tablas desde el panel | Alto: **nunca** en el navegador |

El panel usa `SUPABASE_SERVICE_KEY` si existe y, si no, cae a la anon key.
Sin la service key, RLS bloqueará las lecturas y verás el aviso 403 en las
pestañas de datos. Es el comportamiento correcto: la anon key no debe poder
leer correos ajenos.

Variables opcionales:

```dotenv
CHMODX_PROJECT_ROOT=/ruta/a/LANDINGPYTHON
CHMODX_SITE_URL=https://chmodxcode.pro
CHMODX_GIT_REMOTE=origin
CHMODX_GIT_BRANCH=main
CHMODX_BUILD_COMMAND=python3 scripts/build.py
```

---

## 3. Base de datos

Ejecuta en este orden, en **Supabase → SQL Editor**:

1. `admin/sql/schema.sql` — tablas, índices, RLS y vistas.
2. `admin/sql/002_tracking.sql` — columnas de atribución (`session_id`, UTM, idioma).

Crea:

- `page_views` — visitas (path, referrer, device, country, visitor_id, created_at).
- `leads` — suscriptores (email único, source, status, created_at).
- RLS activado: el sitio solo puede insertar; la lectura queda para el panel.
- Vistas opcionales `analytics_daily` y `analytics_pages` para volúmenes grandes.

### Captura desde la web

La web es estática: el navegador escribe directamente en Supabase con la clave
pública (`sb_publishable_…`), y RLS solo le permite insertar.

1. `scripts/build.py` genera `js/supabase-config.js` con `SUPABASE_URL` y
   `SUPABASE_ANON_KEY` (desde el entorno o desde `admin/.env`). El archivo está
   en `.gitignore`: la clave es pública por diseño, pero no se versiona.
2. `js/tracking.js` registra una fila por página vista con visitante, sesión,
   dispositivo, idioma y UTM. Si las columnas de UTM aún no existen, reintenta
   con el esquema base para no perder la visita.
3. `js/leads.js` conecta cualquier `<form data-cx-lead>` y hace `POST` a `leads`.
   Un 409 (correo repetido) se trata como éxito.
4. Sin `SUPABASE_URL`/`SUPABASE_ANON_KEY`, el script se desactiva solo y el
   sitio funciona igual.

En GitHub Actions las credenciales llegan por **variables del repositorio**
(Settings → Secrets and variables → Actions → Variables):

| Variable | Valor |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_ANON_KEY` | clave pública (`sb_publishable_…`) |

La `SUPABASE_SERVICE_KEY` **nunca** se usa en el build ni viaja al navegador.

Ejemplo de inserción desde el sitio:

```js
await fetch(`${SUPABASE_URL}/rest/v1/page_views`, {
  method: "POST",
  headers: {
    apikey: SUPABASE_ANON_KEY,
    Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    path: location.pathname,
    referrer: document.referrer || null,
    device: matchMedia("(max-width: 768px)").matches ? "mobile" : "desktop",
    visitor_id: localStorage.getItem("cx_visitor"),
  }),
});
```

---

## 4. Uso

```bash
python3 -m admin            # ventana de escritorio
python3 -m admin --web      # interfaz en el navegador (red local)
```

En modo web puedes entrar desde el móvil: `python3 -m admin --web --host 0.0.0.0 --port 8560`.

### Editor

1. Elige **tipo** (repositorio o guía), **categoría** y **nivel**.
2. Escribe el título: el slug se genera solo (puedes editarlo).
3. Redacta el gancho: es la frase que aparece en las tarjetas y en Google.
4. Pega el contenido Markdown. El botón **Estructura maestra** inserta el
   esqueleto de secciones si empiezas de cero.
5. Añade los comandos de Termux en su campo: se envuelven en un bloque `bash`.
6. Revisa la vista previa: ya incluye lo que se publicará.
7. **Guardar borrador** escribe `content/repos/<slug>.md` o
   `content/guias/<slug>.md`. **Guardar y publicar** salta a la pestaña de Git.

También puedes abrir contenido existente con el selector **Abrir existente**.

### Biblioteca de contenido

La pestaña **Contenido** lee `content/repos` y `content/guias` y muestra cada
publicación con su tipo, categoría, nivel, fecha y acciones:

| Acción | Qué hace |
|---|---|
| **Editar** | Carga el archivo en el editor y salta a esa pestaña. |
| **Ver en el sitio** | Abre la URL pública en el navegador. |
| **Eliminar** | Borra el `.md` tras confirmarlo. La página sigue visible hasta que publiques. |

La búsqueda filtra por título, slug o categoría; las píldoras filtran por tipo.
El botón **Nuevo** abre el editor en blanco.

Eliminar no hace commit: el cambio queda pendiente en el árbol de trabajo y se
sube desde **Publicación**, que además ejecuta el build y limpia la carpeta
generada del slug eliminado.

### Tres formas de crear contenido

El selector de la parte superior cambia el modo:

| Modo | Qué hace |
|---|---|
| **Manual** | Formulario clásico, sin ayudas. |
| **Con IA** | OmniRoute redacta el borrador a partir de una idea. |
| **Importar .md** | Carga un archivo del disco, con o sin front matter. |

#### Con IA

Requiere OmniRoute en marcha:

```bash
omniroute serve --daemon
```

Escribe la idea, elige tono y longitud y pulsa **Generar borrador**. El modelo
devuelve un JSON con título, gancho, etiquetas, stack, cuerpo y comandos; el
panel lo vuelca en el formulario, que sigue siendo editable antes de guardar.

- El prompt fija la voz editorial: español neutro, sin voseo, sin emojis y con
  las cinco secciones de la plantilla.
- Se solicita `response_format: json_object`; si el proveedor no lo admite, se
  reintenta sin él.
- Si la respuesta no es JSON válido se reintenta con instrucción estricta y,
  como último recurso, el texto completo se conserva como cuerpo.
- Si un modelo de razonamiento agota el presupuesto de tokens, se reintenta con
  el doble.

Variables (todas opcionales):

```dotenv
OMNIROUTE_BASE_URL=http://127.0.0.1:20128/v1
OMNIROUTE_API_KEY=
OMNIROUTE_MODEL=auto
```

`python3 -m admin --check` comprueba si el servidor responde.

> **Seguridad:** por defecto OmniRoute escucha en `0.0.0.0:20128` sin clave.
> En una red no confiable conviene arrancarlo solo en local
> (`OMNIROUTE_SERVER_HOST=127.0.0.1 omniroute serve --daemon`) o exigir clave
> con `REQUIRE_API_KEY=true` y rellenar `OMNIROUTE_API_KEY`.

#### Importar .md

Acepta `.md`, `.markdown` y `.txt`. Si el archivo trae front matter se respetan
título, slug, resumen, categoría, etiquetas y stack. Si no lo trae, el primer
`# H1` hace de título y el resto es el cuerpo. La importación activa
**Sobrescribir si existe**.

### Plantilla Maestra

Al guardar, el panel envuelve tu texto con la estructura de marca:

```markdown
---
title: "..."
slug: "..."
summary: "..."
category: "..."
difficulty: "..."
stack: ["..."]
tags: ["..."]
updated: "2026-10-29"
repo: ""
featured: false
order: 99
license: "MIT"
---

> **En una frase:** <gancho>

> **Uso responsable:** ...        ← solo en ciberseguridad

<cuerpo escrito por ti>

## Comandos de Termux
```bash
<comandos>
```
```

Reglas:

- El gancho **no se duplica** si ya existe en el cuerpo.
- En ciberseguridad se añade el aviso de uso responsable si falta.
- La sección de comandos solo aparece si hay comandos.
- El front matter es exactamente el que consume `scripts/build.py`.
- **La plantilla no añade ningún cierre comercial.** El artículo termina con
  el bloque `cta-end` que genera `scripts/build.py` y con las tarjetas de
  contenido relacionado. Una sola llamada a la acción por página.

### Analíticas y Leads

Ambas pestañas consultan Supabase al abrirse. Si no hay configuración,
muestran un estado vacío con instrucciones en lugar de romperse.

- **Analíticas**: 7, 30 o 90 días. KPIs, serie diaria, páginas más vistas,
  origen del tráfico y dispositivos. La agregación se hace en el cliente,
  así que funciona con el esquema mínimo; para millones de filas usa las
  vistas `analytics_daily` y `analytics_pages`.
- **Leads**: búsqueda por correo o fuente, KPIs y exportación a
  `admin/exports/leads-AAAAMMDD-HHMMSS.csv`.

### Publicación

El botón **Publicar ahora** ejecuta, en este orden y deteniéndose al primer fallo:

1. `python3 scripts/build.py` (opcional, activado por defecto)
2. `git add -A`
3. `git commit -m "cms: <título>"`
4. `git push origin main`

Cada paso se escribe en la consola con su código de salida y duración.
GitHub Actions toma el relevo y despliega en Pages.

#### Credenciales del push

El panel no depende de que Git tenga credenciales guardadas. Añade un token
con permiso de escritura a `admin/.env`:

```dotenv
CHMODX_GIT_TOKEN=ghp_...
```

Se usa mediante un `credential.helper` efímero y una variable de entorno: el
token nunca se escribe en la URL, ni en `.git/config`, ni en la consola del
panel. Si el remoto lo rechaza, la consola muestra una pista con la solución.

La tarjeta **Repositorio** indica si el token está configurado. Sin él, el
commit local funciona pero el push falla con `Invalid username or token`.

> El commit se hace con `git add -A`, así que arrastra cualquier cambio del
> árbol de trabajo. Publica con el árbol limpio si no quieres mezclar.

#### Seguridad

- Nunca se usa `shell=True`; los argumentos van como lista.
- `shlex.split` para el comando de build definido en el entorno.
- El mensaje de commit se sanea (una línea, sin caracteres de control, sin
  empezar por `-`).
- `GIT_TERMINAL_PROMPT=0`: si faltan credenciales, git falla al instante en
  lugar de quedarse esperando una contraseña.
- El modo **Simulación** hace `add` y `commit` pero no `push`.

---

## 5. Estructura

```
admin/
├── __main__.py        # CLI: --check, --web, --host, --port
├── app.py             # ventana, cabecera, pestañas, barra de estado
├── config.py          # .env, Settings, validación, enmascarado de claves
├── context.py         # estado compartido entre pestañas
├── theme.py           # tokens de color y tema de Flet
├── widgets.py         # tarjetas, KPIs, botones, campos, avisos
├── branding.py        # Plantilla Maestra y copy de marca
├── content.py         # ContentDraft, front matter, validación, guardado
├── analytics.py       # agregación de métricas (funciones puras)
├── supabase_api.py    # cliente REST (httpx)
├── git_ops.py         # subprocess seguro, estado del repo, publicación
├── tabs/
│   ├── editor.py
│   ├── content.py
│   ├── analytics.py
│   ├── leads.py
│   └── publish.py
├── assets/
│   ├── logo.png       # original del logo
│   ├── icon.png       # el mismo logo recortado: cabecera e icono de la app
│   ├── logo.ico       # icono de ventana (Windows)
│   └── fonts/         # tipografías locales opcionales
├── sql/schema.sql
├── .env.example
└── requirements.txt
```

### Identidad visual

La cabecera muestra el logo desde `admin/assets`. Flet sirve esa carpeta como
raíz de recursos (`assets_dir`), así que el panel referencia el archivo por su
nombre y funciona igual en la ventana de escritorio y en `--web`.

| Archivo | Uso |
|---|---|
| `logo.png` | Original que se coloca a mano. Es la fuente de los demás. |
| `icon.png` | Recorte del original sin el margen transparente. Logo de la cabecera y `assets/icon.png` que usa `flet build` al empaquetar. |
| `logo.ico` | Icono de la ventana en Windows (`page.window.icon`). |

Si se cambia `logo.png`, hay que regenerar los derivados:

```bash
python3 - <<'PY'
from PIL import Image

src = Image.open("admin/assets/logo.png").convert("RGBA")
mark = src.crop(src.getchannel("A").getbbox())
side, pad = max(mark.size), round(max(mark.size) * 0.06)
canvas = Image.new("RGBA", (side + pad * 2, side + pad * 2), (0, 0, 0, 0))
canvas.alpha_composite(mark, ((canvas.width - mark.width) // 2,
                              (canvas.height - mark.height) // 2))
icon = canvas.resize((512, 512), Image.LANCZOS)
icon.save("admin/assets/icon.png")
icon.resize((256, 256), Image.LANCZOS).save(
    "admin/assets/logo.ico", format="ICO",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
PY
```

Sin `logo.png` ni `icon.png` la cabecera vuelve a la caja `CX`, y sin
`logo.ico` se omite el icono de ventana: el panel nunca falla por esto.

---

## 6. Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| `403` en Analíticas | RLS bloquea la lectura | Añade `SUPABASE_SERVICE_KEY` al `.env` |
| `404` en Analíticas | Tablas sin crear | Ejecuta `admin/sql/schema.sql` |
| `401` | Clave revocada | Regenera la clave en Supabase |
| «Ya existe \<slug>.md» | El archivo está en el proyecto | Activa **Sobrescribir si existe** |
| El build falla al publicar | Front matter o categoría inválidos | Lee el error en la consola; el push no se ejecuta |
| `git push` falla con «could not read Username» | Sin credenciales | `gh auth login` o configura un token/SSH |
| La ventana no abre en Linux sin GPU | Flutter necesita OpenGL | Usa `--web` o ejecuta en un escritorio con aceleración |

---

## 7. Desarrollo

```bash
python3 -m admin --check    # valida configuración, plantilla e interfaz
```

El comando construye todo el árbol de controles de las cinco pestañas sin
abrir ventana: sirve como prueba de humo en cualquier equipo o en CI.
