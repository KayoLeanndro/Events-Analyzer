from __future__ import annotations

from .models import OpportunityItem


EVENT_HINTS = {
    "event",
    "conference",
    "meetup",
    "summit",
    "webinar",
    "workshop",
    "hackathon",
    "demo day",
    "call for speakers",
}

JOB_HINTS = {
    "job",
    "jobs",
    "hiring",
    "career",
    "vacancy",
    "position",
    "opportunity",
}

PROGRAM_HINTS = {
    "program",
    "programme",
    "ambassador",
    "fellowship",
    "grant",
    "scholarship",
    "incubator",
    "accelerator",
}


def classify_item(item: OpportunityItem, keywords: list[str]) -> OpportunityItem:
    title = item.title.lower()
    summary = item.summary.lower()
    haystack = f"{title} {summary}"

    if not item.kind:
        if any(hint in haystack for hint in JOB_HINTS):
            item.kind = "vaga"
        elif any(hint in haystack for hint in EVENT_HINTS):
            item.kind = "evento"
        elif any(hint in haystack for hint in PROGRAM_HINTS):
            item.kind = "programa"
        else:
            item.kind = "outro"

    score = 0.0
    matched = []
    for keyword in keywords:
        token = keyword.lower().strip()
        if not token:
            continue
        if token in haystack:
            score += 2.0 if token in title else 1.0
            matched.append(token)

    if item.kind == "evento":
        score += 1.2
    elif item.kind == "vaga":
        score += 1.0
    elif item.kind == "programa":
        score += 1.1

    if item.summary:
        score += min(len(item.summary) / 300.0, 1.5)

    if item.region == "nacional":
        score += 0.4

    item.score = round(score, 2)
    item.reason = ", ".join(matched[:5])
    return item
