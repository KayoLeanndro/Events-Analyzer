from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    base_dir: Path
    sources_path: Path
    db_path: Path
    reports_dir: Path
    keywords: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    from_email: str = ""
    to_email: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    daily_time: str = "08:00"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config(base_dir: Path | None = None) -> AppConfig:
    base_dir = base_dir or Path.cwd()
    _load_dotenv(base_dir / ".env")
    data_dir = base_dir / "data"
    reports_dir = base_dir / "reports"
    return AppConfig(
        base_dir=base_dir,
        sources_path=Path(os.getenv("SOURCES_PATH", base_dir / "sources.json")),
        db_path=Path(os.getenv("DB_PATH", data_dir / "events.sqlite3")),
        reports_dir=reports_dir,
        keywords=_load_keywords(),
        regions=_load_list("REGIONS", default=["nacional", "internacional"]),
        from_email=os.getenv("FROM_EMAIL", ""),
        to_email=os.getenv("TO_EMAIL", ""),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_use_tls=_env_bool("SMTP_USE_TLS", True),
        daily_time=os.getenv("DAILY_TIME", "08:00"),
    )


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _load_keywords() -> list[str]:
    raw = os.getenv("KEYWORDS", "")
    if not raw.strip():
        return [
            "ai",
            "artificial intelligence",
            "machine learning",
            "data",
            "cloud",
            "python",
            "developer",
            "engineering",
            "startup",
            "hackathon",
            "meetup",
            "conference",
            "webinar",
            "program",
            "ambassador",
            "fellowship",
            "job",
            "jobs",
            "career",
            "hiring",
            "remote",
    ]
    return [part.strip() for part in raw.split(",") if part.strip()]


def _load_list(name: str, default: list[str] | None = None) -> list[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return default or []
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def load_sources(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict) and "sources" in data:
        data = data["sources"]
    if not isinstance(data, list):
        raise ValueError("sources.json must contain a list or a {sources: [...]} object")
    return data
