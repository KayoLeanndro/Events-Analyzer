from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .classifier import classify_item
from .collector import collect_from_sources, load_source_specs
from .config import AppConfig, load_sources
from .notifier import send_email
from .store import Store
from .summarizer import build_digest


def run_scan(config: AppConfig) -> tuple[list, list]:
    raw_sources = load_sources(config.sources_path)
    sources = load_source_specs(raw_sources)
    sources = _filter_sources_by_region(sources, config.regions)
    store = Store(config.db_path)
    collected = collect_from_sources(sources)
    processed = []
    inserted = []
    for item in collected:
        item = classify_item(item, config.keywords)
        processed.append(item)
        if store.upsert_item(item):
            inserted.append(item)
    return processed, inserted


def build_report(config: AppConfig, hours: int = 24) -> tuple[str, list]:
    store = Store(config.db_path)
    items = store.list_recent_items(hours=hours)
    filtered_items = _filter_items_by_region(items, config.regions)
    report = build_digest(filtered_items, generated_at=datetime.now(), regions=config.regions)
    return report, filtered_items


def write_report(config: AppConfig, body: str) -> Path:
    config.reports_dir.mkdir(parents=True, exist_ok=True)
    file_path = config.reports_dir / f"{datetime.now():%Y-%m-%d}.md"
    file_path.write_text(body, encoding="utf-8")
    return file_path


def deliver_report(config: AppConfig, body: str) -> None:
    send_email(
        subject="Resumo diario de tecnologia",
        body=body,
        from_email=config.from_email,
        to_email=config.to_email,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_password=config.smtp_password,
        use_tls=config.smtp_use_tls,
    )


def can_deliver_report(config: AppConfig) -> bool:
    return bool(config.from_email and config.to_email and config.smtp_host)


def _filter_sources_by_region(sources, regions: list[str]):
    if not regions:
        return sources
    normalized = {region.lower().strip() for region in regions if region.strip()}
    return [source for source in sources if source.region.lower().strip() in normalized]


def _filter_items_by_region(items, regions: list[str]):
    if not regions:
        return items
    normalized = {region.lower().strip() for region in regions if region.strip()}
    return [item for item in items if item.region.lower().strip() in normalized]
