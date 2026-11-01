"""Cliente de OmniRoute para redactar borradores con IA.

OmniRoute expone una API compatible con OpenAI en ``<base>/chat/completions``.
Se usa ``httpx`` y un prompt de sistema que fija la voz editorial del sitio.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:20128/v1"
DEFAULT_MODEL = "auto"


class OmniRouteError(RuntimeError):
    """Error de conexión o de respuesta de OmniRoute."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class OmniRouteConfig:
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    model: str = DEFAULT_MODEL
    timeout: float = 150.0

    def normalized_base_url(self) -> str:
        url = (self.base_url or DEFAULT_BASE_URL).strip().rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        return url


SYSTEM_PROMPT = """Eres el editor técnico de CHMODX, un sitio de ciberseguridad, Python y Termux.

Escribes en español neutro e internacional. Reglas obligatorias:
- Nunca uses voseo ni regionalismos (nada de "podés", "tenés", "fijate", "laburo").
- Nada de emojis.
- Nada de introducciones del tipo "en este artículo exploraremos" ni de conclusiones vacías.
- Frases cortas, voz activa, ejemplos concretos y ejecutables.
- No inventes versiones, resultados, cifras ni enlaces que no puedas sostener.
- Si el tema es de ciberseguridad, incluye una advertencia de uso responsable y legal.
- Los comandos deben ser realistas y funcionar en un entorno limpio.

Devuelve EXCLUSIVAMENTE un objeto JSON válido, sin texto antes ni después y sin
cercado de código, con esta forma exacta:

{
  "title": "título de 40 a 90 caracteres, sin comillas internas",
  "summary": "una sola frase de 60 a 200 caracteres que resuma el valor",
  "tags": ["3 a 5 etiquetas en minúsculas"],
  "stack": ["tecnologías concretas usadas"],
  "body": "cuerpo en Markdown",
  "commands": "comandos de terminal en texto plano, uno por línea"
}

El campo "body" debe seguir esta estructura de secciones, en este orden:

## Qué vas a construir
## Requisitos
## El código
## Cómo ejecutarlo
## Errores frecuentes

No incluyas la sección "Siguiente paso", ni enlaces al curso, ni el front
matter: el sistema los añade después.
"""

TONE_WORDS = {
    "Técnico y directo": "técnico, directo, sin rodeos",
    "Didáctico": "didáctico, explicando el porqué de cada paso",
    "Divulgativo": "divulgativo, con analogías y sin jerga innecesaria",
}

LENGTH_WORDS = {
    "Corta (~600 palabras)": 600,
    "Media (~1000 palabras)": 1000,
    "Larga (~1600 palabras)": 1600,
}


class OmniRouteClient:
    """Cliente mínimo de la API de OmniRoute."""

    def __init__(self, config: OmniRouteConfig) -> None:
        self.config = config
        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self._client = httpx.Client(
            base_url=config.normalized_base_url(),
            timeout=config.timeout,
            headers=headers,
        )

    # ------------------------------------------------------------------ estado
    def health(self) -> tuple[bool, str]:
        """Comprueba que el servidor responde.

        ``/v1/models`` exige clave; ``/api/health`` no, así que se usa ese.
        """
        root = self.config.normalized_base_url()[: -len("/v1")]
        try:
            response = self._client.get(f"{root}/api/health")
        except httpx.HTTPError:
            return False, (
                "OmniRoute no responde. Arráncalo con: omniroute serve --daemon"
            )
        if response.status_code >= 400:
            return False, f"OmniRoute respondió {response.status_code}."
        return True, "OmniRoute disponible."

    def models(self) -> list[str]:
        try:
            response = self._client.get("/models")
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return []
        return [str(item.get("id")) for item in data.get("data", []) if item.get("id")]

    # ------------------------------------------------------------------ chat
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.6,
        max_tokens: int = 8000,
        json_mode: bool = False,
    ) -> str:
        def call(budget: int, use_json: bool) -> httpx.Response:
            payload = {
                "model": model or self.config.model or DEFAULT_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": budget,
                "stream": False,
            }
            if use_json:
                payload["response_format"] = {"type": "json_object"}
            try:
                return self._client.post("/chat/completions", json=payload)
            except httpx.TimeoutException as exc:
                raise OmniRouteError("OmniRoute tardó demasiado en responder.") from exc
            except httpx.HTTPError as exc:
                raise OmniRouteError(
                    "No se pudo conectar con OmniRoute. Arráncalo con: "
                    "omniroute serve --daemon"
                ) from exc

        response = call(max_tokens, json_mode)

        # Algunos proveedores no aceptan response_format: se reintenta sin él.
        if json_mode and response.status_code == 400:
            json_mode = False
            response = call(max_tokens, False)

        # Los modelos de razonamiento agotan el presupuesto pensando y
        # OmniRoute devuelve 502. Se reintenta una vez con el doble.
        if response.status_code == 502 and "truncat" in response.text.lower():
            response = call(max_tokens * 2, json_mode)

        if response.status_code >= 400:
            detail = response.text.strip()[:200]
            raise OmniRouteError(
                f"OmniRoute respondió {response.status_code}: {detail}",
                response.status_code,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise OmniRouteError("OmniRoute devolvió una respuesta que no es JSON.") from exc

        try:
            return str(data["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError, TypeError) as exc:
            raise OmniRouteError("Respuesta de OmniRoute sin contenido.") from exc

    # ------------------------------------------------------------------ redacción
    def generate(
        self,
        brief: str,
        *,
        kind_label: str = "Repositorio",
        category_label: str = "Python",
        level: str = "Principiante",
        tone: str = "Técnico y directo",
        length: str = "Media (~1000 palabras)",
    ) -> dict[str, Any]:
        """Genera un borrador estructurado a partir de una idea."""
        words = LENGTH_WORDS.get(length, 1000)
        user_prompt = (
            f"Tema: {brief.strip()}\n"
            f"Tipo de contenido: {kind_label}\n"
            f"Categoría: {category_label}\n"
            f"Nivel del lector: {level}\n"
            f"Tono: {TONE_WORDS.get(tone, TONE_WORDS['Técnico y directo'])}\n"
            f"Extensión aproximada del cuerpo: {words} palabras\n"
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        raw = self.chat(messages, json_mode=True)
        data = extract_json(raw)

        if data is None:
            # Segundo intento, más determinista y con la instrucción explícita.
            retry = messages + [
                {
                    "role": "user",
                    "content": (
                        "IMPORTANTE: responde únicamente con el objeto JSON pedido, "
                        "sin explicaciones, sin texto antes ni después y sin cercado."
                    ),
                }
            ]
            raw = self.chat(retry, temperature=0.2, json_mode=True)
            data = extract_json(raw)

        return draft_from_data(data, raw, brief)


# --------------------------------------------------------------------------- #
# Parseo tolerante
# --------------------------------------------------------------------------- #
def extract_json(text: str) -> dict[str, Any] | None:
    """Extrae el primer objeto JSON de una respuesta, aunque venga con cercado."""
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```[a-zA-Z]*\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)

    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = clean[start : end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        # Reintento: comillas simples y comas finales, errores habituales de un LLM.
        repaired = re.sub(r",\s*([}\]])", r"\1", candidate.replace("'", '"'))
        try:
            data = json.loads(repaired)
        except json.JSONDecodeError:
            return None

    return data if isinstance(data, dict) else None


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _short_title(text: str, limit: int = 80) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    cut = clean[:limit].rsplit(" ", 1)[0]
    return cut or clean[:limit]


def draft_from_data(data: dict[str, Any] | None, raw: str, brief: str) -> dict[str, Any]:
    """Normaliza los datos ya parseados (o cae al texto crudo)."""
    if data is None:
        # Sin JSON válido se conserva el texto como cuerpo: nunca se pierde.
        return {
            "title": _short_title(brief),
            "summary": "",
            "tags": [],
            "stack": [],
            "body": raw.strip(),
            "commands": "",
            "fallback": True,
        }

    return {
        "title": str(data.get("title") or brief).strip()[:120],
        "summary": str(data.get("summary") or "").strip()[:220],
        "tags": _as_list(data.get("tags"))[:6],
        "stack": _as_list(data.get("stack"))[:5],
        "body": str(data.get("body") or "").strip(),
        "commands": str(data.get("commands") or "").strip(),
        "fallback": False,
    }


def parse_draft(raw: str, brief: str) -> dict[str, Any]:
    """Convierte una respuesta cruda del modelo en campos del formulario."""
    return draft_from_data(extract_json(raw), raw, brief)
