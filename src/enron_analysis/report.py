import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .ingest import QualityCounts


def write_quality_report(path: Path, quality: QualityCounts) -> None:
    """Write aggregate counters only; no message-level values are accepted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(quality), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_privacy_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_findings_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
