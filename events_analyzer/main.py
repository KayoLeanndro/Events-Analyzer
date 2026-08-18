from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta

from .config import load_config
from .notifier import EmailDeliveryError
from .pipeline import build_report, can_deliver_report, deliver_report, run_scan, write_report


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--log-level", default="INFO", help="Logging level")
    common.add_argument(
        "--regions",
        default=argparse.SUPPRESS,
        help="Comma-separated regions to include, e.g. nacional,internacional",
    )

    parser = argparse.ArgumentParser(
        description="Daily technology events, jobs and programs scanner",
        parents=[common],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scan", help="Collect new items and store them", parents=[common])
    digest_parser = subparsers.add_parser("digest", help="Build a digest from the last 24 hours", parents=[common])
    digest_parser.add_argument("--hours", type=int, default=24, help="Lookback window for digest")
    send_parser = subparsers.add_parser("send", help="Build and email the digest", parents=[common])
    send_parser.add_argument("--hours", type=int, default=24, help="Lookback window for digest")
    loop_parser = subparsers.add_parser("loop", help="Run forever and send a digest at the configured time", parents=[common])
    loop_parser.add_argument("--once", action="store_true", help="Run one digest immediately before waiting")

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, str(getattr(args, "log_level", "INFO")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    config = load_config()
    config.regions = _resolve_regions(getattr(args, "regions", ""), config.regions)

    if args.command == "scan":
        _ensure_sources_hint(config)
        processed, inserted = run_scan(config)
        report = _format_scan_report(processed, inserted)
        report_path = write_report(config, report)
        print(report)
        print(f"Saved to {report_path}")
        return 0

    if args.command == "digest":
        report, items = build_report(config, hours=args.hours)
        report_path = write_report(config, report)
        print(report)
        print(f"Items: {len(items)}")
        print(f"Saved to {report_path}")
        return 0

    if args.command == "send":
        report, items = build_report(config, hours=args.hours)
        report_path = write_report(config, report)
        if not items:
            print(f"No items found. Report saved to {report_path}.")
            return 0
        if can_deliver_report(config):
            try:
                deliver_report(config, report)
                print(f"Sent digest with {len(items)} items.")
            except EmailDeliveryError as exc:
                print(f"Digest generated with {len(items)} items, but sending failed: {exc}")
                print(f"Report saved to {report_path}.")
        else:
            print(
                f"Digest generated with {len(items)} items but e-mail is not configured. "
                f"Report saved to {report_path}."
            )
        return 0

    if args.command == "loop":
        _run_loop(config, run_once=args.once)
        return 0

    parser.print_help()
    return 1


def _ensure_sources_hint(config) -> None:
    if not config.sources_path.exists():
        print(
            f"Sources file not found at {config.sources_path}. "
            "Create it from sources.example.json before collecting."
        )


def _format_scan_report(processed, inserted) -> str:
    lines = [
        "Scan completed",
        f"Processed: {len(processed)}",
        f"New items: {len(inserted)}",
        "",
    ]
    for item in inserted[:20]:
        lines.append(f"- {item.kind}: {item.title} [{item.source_name}]")
        lines.append(f"  {item.url}")
    if not inserted:
        lines.append("No new items found.")
    return "\n".join(lines) + "\n"


def _run_loop(config, run_once: bool) -> None:
    if run_once:
        _run_cycle(config)
    while True:
        sleep_seconds = _seconds_until_next_run(config.daily_time)
        print(f"Next run in {sleep_seconds} seconds.")
        time.sleep(sleep_seconds)
        _run_cycle(config)


def _run_cycle(config) -> None:
    run_scan(config)
    report, items = build_report(config)
    write_report(config, report)
    if items and config.from_email and config.to_email and config.smtp_host:
        try:
            deliver_report(config, report)
            print(f"Digest sent with {len(items)} items.")
        except EmailDeliveryError as exc:
            print(f"Digest ready with {len(items)} items, but sending failed: {exc}")
    else:
        print(f"Digest ready with {len(items)} items.")


def _seconds_until_next_run(daily_time: str) -> int:
    hour, minute = (int(part) for part in daily_time.split(":", 1))
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return max(1, int((target - now).total_seconds()))


def _resolve_regions(cli_value: str, default_regions: list[str]) -> list[str]:
    if cli_value.strip():
        return [part.strip().lower() for part in cli_value.split(",") if part.strip()]
    return default_regions


if __name__ == "__main__":
    raise SystemExit(main())
