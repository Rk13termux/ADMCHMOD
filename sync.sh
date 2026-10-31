#!/usr/bin/env bash
# Sincroniza admin/ desde el proyecto web y publica el cambio.
#
#   ./sync.sh /ruta/a/LANDINGPYTHON/admin
#
# Nunca copia .env, caché ni exportaciones.
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
git push
