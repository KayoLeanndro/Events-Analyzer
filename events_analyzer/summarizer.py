from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .models import OpportunityItem


def build_digest(
    items: list[OpportunityItem],
    generated_at: datetime | None = None,
    limit_per_group: int = 5,
    regions: list[str] | None = None,
) -> str:
    generated_at = generated_at or datetime.now()
    regions = [region.lower().strip() for region in regions or [] if region.strip()]
    if regions:
        items = [item for item in items if item.region.lower() in regions]

    groups: dict[str, list[OpportunityItem]] = defaultdict(list)
    for item in sorted(items, key=lambda current: (current.region, current.kind, -current.score, current.title.lower())):
        groups[item.region or "internacional"].append(item)

    lines: list[str] = []
    lines.append(f"Resumo diario de tecnologia")
    lines.append(f"Gerado em: {generated_at:%Y-%m-%d %H:%M}")
    if regions:
        lines.append(f"Filtro de regiao: {', '.join(regions)}")
    lines.append("")

    if not items:
        lines.append("Nenhum item novo encontrado no periodo.")
        return "\n".join(lines)

    highlights = sorted(items, key=lambda current: (-current.score, current.title.lower()))[:5]
    lines.append("Destaques")
    for item in highlights:
        lines.append(_format_item(item))
    lines.append("")

    region_order = regions or ["nacional", "internacional", "local", "outro"]
    for region in region_order:
        bucket = groups.get(region, [])
        if not bucket:
            continue
        lines.append(_pretty_region(region))
        by_kind: dict[str, list[OpportunityItem]] = defaultdict(list)
        for item in bucket:
            by_kind[item.kind or "outro"].append(item)
        for kind in ("evento", "vaga", "programa", "outro"):
            kind_bucket = by_kind.get(kind, [])
            if not kind_bucket:
                continue
            lines.append(f"{kind.capitalize()}")
            for item in kind_bucket[:limit_per_group]:
                lines.append(_format_item(item))
        lines.append("")

    return "\n".join(line.rstrip() for line in lines).strip() + "\n"


def _format_item(item: OpportunityItem) -> str:
    published = f" | {item.published_at:%Y-%m-%d}" if item.published_at else ""
    source = f" [{item.source_name} | {item.region}]"
    score = f" score={item.score:.1f}"
    summary = f" - {item.summary}" if item.summary else ""
    return f"- {item.title}{source}{published}{score}{summary}\n  {item.url}"


def _pretty_region(region: str) -> str:
    mapping = {
        "nacional": "Nacional",
        "internacional": "Internacional",
        "local": "Local",
        "outro": "Outro",
    }
    return mapping.get(region.lower(), region.capitalize())
