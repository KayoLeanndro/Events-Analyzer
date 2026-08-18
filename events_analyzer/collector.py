from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import OpportunityItem, SourceSpec

LOGGER = logging.getLogger(__name__)


def load_source_specs(raw_sources: list[dict]) -> list[SourceSpec]:
    return [SourceSpec.from_dict(source) for source in raw_sources]


def collect_from_sources(sources: Iterable[SourceSpec], timeout: int = 20) -> list[OpportunityItem]:
    items: list[OpportunityItem] = []
    with _build_session() as session:
        for source in sources:
            try:
                fetched = collect_from_source(source, session=session, timeout=timeout)
                items.extend(fetched)
            except Exception as exc:  # pragma: no cover - resilient by design
                LOGGER.warning("source %s failed: %s", source.name, exc)
    return items


def collect_from_source(source: SourceSpec, session: requests.Session | None = None, timeout: int = 20) -> list[OpportunityItem]:
    if session is None:
        with requests.Session() as client:
            response = client.get(source.url, timeout=timeout, headers={"User-Agent": "EventsAnalyzer/1.0"})
    else:
        response = session.get(source.url, timeout=timeout, headers={"User-Agent": "EventsAnalyzer/1.0"})
    response.raise_for_status()

    if source.parser.lower() == "html":
        return _parse_html(response.text, source)
    return _parse_rss_or_atom(response.text, source)


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _parse_rss_or_atom(xml_text: str, source: SourceSpec) -> list[OpportunityItem]:
    root = ET.fromstring(xml_text)
    items: list[OpportunityItem] = []

    if root.tag.endswith("feed"):
        namespaces = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", namespaces):
            title = _clean_text(_find_text(entry, "atom:title", namespaces))
            link = _find_atom_link(entry, namespaces)
            summary = _clean_text(_find_text(entry, "atom:summary", namespaces) or _find_text(entry, "atom:content", namespaces))
            published_at = _parse_datetime(_find_text(entry, "atom:published", namespaces) or _find_text(entry, "atom:updated", namespaces))
            if title:
                items.append(_build_item(title, link, summary, published_at, source))
    else:
        for entry in root.findall(".//item"):
            title = _clean_text(_find_text(entry, "title"))
            link = _clean_text(_find_text(entry, "link"))
            summary = _clean_text(_find_text(entry, "description") or _find_text(entry, "summary"))
            published_at = _parse_datetime(_find_text(entry, "pubDate") or _find_text(entry, "date"))
            if title:
                items.append(_build_item(title, link, summary, published_at, source))

    return items


def _parse_html(html_text: str, source: SourceSpec) -> list[OpportunityItem]:
    soup = BeautifulSoup(html_text, "html.parser")
    items: list[OpportunityItem] = []

    if source.item_selector:
        for node in soup.select(source.item_selector):
            title = _select_text(node, source.title_selector) if source.title_selector else _guess_title(node)
            link = _select_link(node, source.link_selector) if source.link_selector else _guess_link(node, source.url)
            summary = _select_text(node, source.summary_selector) if source.summary_selector else _guess_summary(node)
            published_at = _parse_html_date(node, source.date_selector)
            if title:
                items.append(_build_item(title, link, summary, published_at, source))
        return items

    for article in soup.find_all(["article", "li", "div"]):
        title = _guess_title(article)
        link = _guess_link(article, source.url)
        summary = _guess_summary(article)
        if title and link:
            items.append(_build_item(title, link, summary, None, source))

    return _dedupe(items)


def _build_item(title: str, link: str, summary: str, published_at: datetime | None, source: SourceSpec) -> OpportunityItem:
    return OpportunityItem(
        title=_clean_text(title),
        url=_clean_text(link),
        source_name=source.name,
        kind=source.kind,
        region=source.region,
        country=source.country,
        summary=_clean_text(summary),
        published_at=published_at,
        raw={"source_url": source.url, "region": source.region, "country": source.country},
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except Exception:
        pass
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _parse_html_date(node, selector: str) -> datetime | None:
    if not selector:
        return None
    candidate = node.select_one(selector)
    if candidate is None:
        return None
    text = candidate.get("datetime") or candidate.get_text(" ", strip=True)
    return _parse_datetime(text)


def _find_text(node, selector: str, namespaces: dict[str, str] | None = None) -> str:
    if namespaces:
        found = node.find(selector, namespaces)
    else:
        found = node.find(selector)
    if found is None:
        return ""
    return _clean_text(found.text)


def _find_atom_link(entry, namespaces: dict[str, str]) -> str:
    link = entry.find("atom:link", namespaces)
    if link is None:
        return ""
    href = link.attrib.get("href", "")
    return _clean_text(href)


def _select_text(node, selector: str) -> str:
    if not selector:
        return ""
    found = node.select_one(selector)
    if found is None:
        return ""
    return _clean_text(found.get_text(" ", strip=True))


def _select_link(node, selector: str) -> str:
    if not selector:
        return ""
    found = node.select_one(selector)
    if found is None:
        return ""
    href = found.get("href") or found.get("src") or found.get_text(" ", strip=True)
    return _clean_text(href)


def _guess_title(node) -> str:
    for tag in ("h1", "h2", "h3", "h4", "a"):
        found = node.find(tag)
        if found:
            text = _clean_text(found.get_text(" ", strip=True))
            if text:
                return text
    text = _clean_text(node.get_text(" ", strip=True))
    if len(text) > 30:
        return text[:120]
    return ""


def _guess_link(node, base_url: str) -> str:
    link = node.find("a", href=True)
    if not link:
        return ""
    return urljoin(base_url, link["href"])


def _guess_summary(node) -> str:
    text = _clean_text(node.get_text(" ", strip=True))
    if len(text) <= 120:
        return text
    return text[:240]


def _clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _dedupe(items: list[OpportunityItem]) -> list[OpportunityItem]:
    seen: set[str] = set()
    deduped: list[OpportunityItem] = []
    for item in items:
        key = item.key
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
