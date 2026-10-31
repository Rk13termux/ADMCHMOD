#!/usr/bin/env bash
# Sincroniza admin/ desde el proyecto web y publica el cambio.
#
#   ./sync.sh /ruta/a/LANDINGPYTHON/admin
#
# Nunca copia .env, caché ni exportaciones.
# El token se toma de CHMODX_GIT_TOKEN o del .env del proyecto de origen, y
# se usa con un credential.helper efímero: no queda en la URL ni en .git/config.
set -euo pipefail

SRC="${1:-../LANDINGPYTHON/admin}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HERE/admin"

if [ ! -d "$SRC" ]; then
    echo "No existe el origen: $SRC" >&2
    echo "Uso: ./sync.sh /ruta/a/LANDINGPYTHON/admin" >&2
    exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
    echo "Falta rsync." >&2
    exit 1
fi

rsync -a --delete \
    --exclude '.env' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude 'exports/' \
    --exclude 'assets/fonts/*.ttf' \
    "$SRC/" "$DEST/"

cd "$HERE"
git add -A
if git diff --cached --quiet; then
    echo "Sin cambios que sincronizar."
    exit 0
fi

git commit -m "sync: $(date '+%Y-%m-%d %H:%M')"

# Token: primero el entorno, luego el .env del proyecto de origen.
TOKEN="${CHMODX_GIT_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$SRC/.env" ]; then
    TOKEN="$(sed -n 's/^CHMODX_GIT_TOKEN=//p' "$SRC/.env" | head -1 | tr -d '"'"'"' \r')"
fi

if [ -n "$TOKEN" ]; then
    CHMODX_GIT_TOKEN="$TOKEN" GIT_TERMINAL_PROMPT=0 git \
        -c credential.helper='' \
        -c credential.helper='!f() { echo username=x-access-token; echo "password=$CHMODX_GIT_TOKEN"; }; f' \
        push
else
    echo "Aviso: sin CHMODX_GIT_TOKEN; se usa la configuración de Git del sistema." >&2
    git push
fi
