"""Cliente mínimo de Supabase sobre la API REST (PostgREST).

Se usa ``httpx`` en lugar del SDK oficial para mantener el panel ligero y
controlar tiempos de espera, errores y encabezados de forma explícita.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


class SupabaseError(RuntimeError):
    """Error de configuración o de respuesta de Supabase."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class TableStatus:
    table: str
    ok: bool
    detail: str


def _friendly_error(status: int, body: str, table: str) -> str:
    if status == 401:
        return "Clave de Supabase inválida o revocada (401)."
    if status == 403:
        return (
            f"RLS bloquea la lectura de '{table}' (403). Añade SUPABASE_SERVICE_KEY "
            "o una política de lectura para el panel."
        )
    if status == 404:
        return f"La tabla '{table}' no existe (404). Ejecuta admin/sql/schema.sql."
    if status == 429:
        return "Demasiadas peticiones a Supabase (429). Espera unos segundos."
    detail = body.strip()
    if len(detail) > 180:
        detail = detail[:180] + "…"
    return f"Supabase respondió {status}: {detail}"


class SupabaseClient:
    """Lecturas tipadas sobre las tablas del proyecto."""

    def __init__(self, url: str, key: str, *, timeout: float = 15.0) -> None:
        if not url or not key:
            raise SupabaseError("Faltan SUPABASE_URL o la clave de acceso.")
        self._base = url.rstrip("/") + "/rest/v1"
        self._key = key
        self._client = httpx.Client(
            base_url=self._base,
            timeout=timeout,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
            },
        )

    # ------------------------------------------------------------------ interno
    def _get(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        try:
            response = self._client.get(f"/{table}", params=params)
        except httpx.TimeoutException as exc:
            raise SupabaseError("Supabase no respondió a tiempo.") from exc
        except httpx.HTTPError as exc:
            raise SupabaseError(f"No se pudo conectar con Supabase: {exc}") from exc

        if response.status_code >= 400:
            raise SupabaseError(
                _friendly_error(response.status_code, response.text, table),
                response.status_code,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise SupabaseError("Supabase devolvió una respuesta que no es JSON.") from exc

        if not isinstance(data, list):
            raise SupabaseError("Respuesta inesperada de Supabase (se esperaba una lista).")
        return data

    # ------------------------------------------------------------------ público
    def probe(self, tables: tuple[str, ...] = ("page_views", "leads")) -> list[TableStatus]:
        """Comprueba qué tablas son legibles con la clave actual."""
        statuses: list[TableStatus] = []
        for table in tables:
            try:
                response = self._client.get(
                    f"/{table}", params={"select": "id", "limit": "1"}
                )
            except httpx.HTTPError as exc:
                statuses.append(TableStatus(table, False, f"Sin conexión: {exc}"))
                continue

            if response.status_code >= 400:
                statuses.append(
                    TableStatus(
                        table,
                        False,
                        _friendly_error(response.status_code, response.text, table),
                    )
                )
            else:
                statuses.append(TableStatus(table, True, "accesible"))
        return statuses

    FULL_COLUMNS = (
        "path,referrer,device,country,visitor_id,created_at,"
        "session_id,utm_source,utm_medium,utm_campaign,utm_content,language"
    )
    BASE_COLUMNS = "path,referrer,device,country,visitor_id,created_at"

    def page_views(self, days: int = 30, *, limit: int = 20000) -> list[dict[str, Any]]:
        """Filas de visitas de los últimos ``days`` días.

        Si la base aún no tiene las columnas de UTM (migración 002), se
        reintenta con el esquema base en lugar de romper la pestaña.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        params = {
            "select": self.FULL_COLUMNS,
            "created_at": f"gte.{since.isoformat()}",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        try:
            return self._get("page_views", params)
        except SupabaseError as exc:
            if exc.status == 400:
                params["select"] = self.BASE_COLUMNS
                return self._get("page_views", params)
            raise

    def leads(self, *, search: str = "", limit: int = 500) -> list[dict[str, Any]]:
        """Suscriptores capturados, del más reciente al más antiguo."""
        params: dict[str, str] = {
            "select": "id,email,source,status,created_at",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        term = search.strip()
        if term:
            params["or"] = f"(email.ilike.%{term}%,source.ilike.%{term}%)"
        return self._get("leads", params)

    def close(self) -> None:
        self._client.close()
