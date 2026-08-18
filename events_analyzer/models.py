from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_url(url: str) -> str:
    url = _safe_text(url)
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme:
        return url
    return url


@dataclass(slots=True)
class SourceSpec:
    name: str
    url: str
    parser: str = "rss"
    kind: str = ""
    region: str = "internacional"
    country: str = ""
    item_selector: str = ""
    title_selector: str = ""
    link_selector: str = ""
    summary_selector: str = ""
    date_selector: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceSpec":
        return cls(
            name=_safe_text(data.get("name")),
            url=_normalize_url(data.get("url", "")),
            parser=_safe_text(data.get("parser", "rss")) or "rss",
            kind=_safe_text(data.get("kind", "")),
            region=_safe_text(data.get("region", "internacional")) or "internacional",
            country=_safe_text(data.get("country", "")),
            item_selector=_safe_text(data.get("item_selector", "")),
            title_selector=_safe_text(data.get("title_selector", "")),
            link_selector=_safe_text(data.get("link_selector", "")),
            summary_selector=_safe_text(data.get("summary_selector", "")),
            date_selector=_safe_text(data.get("date_selector", "")),
        )


@dataclass(slots=True)
class OpportunityItem:
    title: str
    url: str
    source_name: str
    kind: str = ""
    region: str = "internacional"
    country: str = ""
    company: str = ""
    summary: str = ""
    published_at: datetime | None = None
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    score: float = 0.0
    reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        normalized_url = _normalize_url(self.url)
        if normalized_url:
            return normalized_url
        return f"{self.source_name}:{self.title}".strip().lower()
