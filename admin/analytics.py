"""Agregación de métricas a partir de las filas de ``page_views``.

Se calcula en el cliente para que el panel funcione con cualquier esquema
mínimo. Para volúmenes grandes conviene una vista materializada en Supabase;
el README explica cómo.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

ACADEMY_PREFIX = "/academia"


@dataclass
class AnalyticsSummary:
    total_views: int = 0
    unique_visitors: int = 0
    academy_views: int = 0
    academy_from_cta: int = 0
    days: list[tuple[str, int]] = field(default_factory=list)
    pages: list[tuple[str, int]] = field(default_factory=list)
    sources: list[tuple[str, int]] = field(default_factory=list)
    devices: list[tuple[str, int]] = field(default_factory=list)
    cta_blocks: list[tuple[str, int]] = field(default_factory=list)
    cta_campaigns: list[tuple[str, int]] = field(default_factory=list)
    rows: int = 0

    @property
    def conversion(self) -> float:
        return (self.academy_views / self.total_views * 100) if self.total_views else 0.0

    @property
    def cta_conversion(self) -> float:
        """Porcentaje de visitas que llegan a la academia desde un CTA interno."""
        return (self.academy_from_cta / self.total_views * 100) if self.total_views else 0.0

    @property
    def has_utm(self) -> bool:
        return bool(self.cta_blocks)

    @property
    def daily_average(self) -> float:
        active = len([count for _, count in self.days if count])
        return (self.total_views / active) if active else 0.0


def _parse_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


def _source_label(referrer: str, utm_source: str | None = None) -> str:
    """Clasifica el origen: primero el UTM externo, después el referrer."""
    if utm_source and utm_source not in {"contenido"}:
        return utm_source.lower()
    if not referrer:
        return "directo"
    try:
        host = urlparse(referrer).netloc.lower().replace("www.", "")
    except ValueError:
        return "otro"
    if not host:
        return "directo"
    if "chmodxcode" in host:
        return "interno"
    if "google" in host:
        return "google"
    if "t.me" in host or "telegram" in host:
        return "telegram"
    if "instagram" in host:
        return "instagram"
    if "tiktok" in host:
        return "tiktok"
    if "youtube" in host:
        return "youtube"
    if "github" in host:
        return "github"
    return host


def summarize(rows: list[dict[str, Any]], days: int = 30) -> AnalyticsSummary:
    """Resume las filas de visitas en métricas listas para pintar."""
    summary = AnalyticsSummary(rows=len(rows))
    if not rows:
        summary.days = _empty_days(days)
        return summary

    visitors: set[str] = set()
    per_day: Counter[str] = Counter()
    per_page: Counter[str] = Counter()
    per_source: Counter[str] = Counter()
    per_device: Counter[str] = Counter()
    per_cta: Counter[str] = Counter()
    per_campaign: Counter[str] = Counter()

    for row in rows:
        path = str(row.get("path") or "/")
        per_page[path] += 1

        visitor = row.get("visitor_id")
        if visitor:
            visitors.add(str(visitor))

        in_academy = path.startswith(ACADEMY_PREFIX)
        if in_academy:
            summary.academy_views += 1

        parsed = _parse_date(str(row.get("created_at") or ""))
        if parsed:
            per_day[parsed.isoformat()] += 1

        utm_source = row.get("utm_source")
        utm_medium = row.get("utm_medium")
        utm_content = row.get("utm_content")
        utm_campaign = row.get("utm_campaign")

        per_source[_source_label(str(row.get("referrer") or ""), utm_source)] += 1
        per_device[str(row.get("device") or "desconocido").lower()] += 1

        # CTA interno: los enlaces del sitio siempre llevan utm_source=contenido.
        if utm_source == "contenido" and utm_medium:
            per_cta[str(utm_content or utm_medium)] += 1
            if utm_campaign:
                per_campaign[str(utm_campaign)] += 1
            if in_academy:
                summary.academy_from_cta += 1

    summary.total_views = len(rows)
    summary.unique_visitors = len(visitors) or len(rows)
    summary.pages = per_page.most_common(8)
    summary.sources = per_source.most_common(6)
    summary.devices = per_device.most_common(4)
    summary.cta_blocks = per_cta.most_common(8)
    summary.cta_campaigns = per_campaign.most_common(5)

    filled = _empty_days(days)
    summary.days = [(day, per_day.get(day, 0)) for day, _ in filled]

    return summary


def _empty_days(days: int) -> list[tuple[str, int]]:
    today = datetime.now(timezone.utc).date()
    return [((today - timedelta(days=offset)).isoformat(), 0) for offset in range(days - 1, -1, -1)]
