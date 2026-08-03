#!/usr/bin/env python3
"""Produce a deterministic audit of a linear stacked Platform phase history."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from stacked_phase_history_git import audit
from stacked_phase_history_metadata import metadata_from_event, parse_stacked_metadata
from stacked_phase_history_model import CATEGORIES, AuditError, classify

__all__ = (
    "AuditError",
    "CATEGORIES",
    "audit",
    "classify",
    "main",
    "metadata_from_event",
    "parse_stacked_metadata",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path)
    parser.add_argument("--repository")
    parser.add_argument("--token")
    parser.add_argument("--accepted-base")
    parser.add_argument("--pr-base")
    parser.add_argument("--head")
    parser.add_argument("--phase", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.event:
        event = json.loads(args.event.read_text(encoding="utf-8"))
        metadata = metadata_from_event(
            event,
            repository=args.repository or os.getenv("GITHUB_REPOSITORY"),
            token=args.token or os.getenv("GITHUB_TOKEN"),
        )
    else:
        if not all((args.accepted_base, args.pr_base, args.head, args.phase)):
            parser.error(
                "provide --event or all of --accepted-base, --pr-base, --head, --phase"
            )
        metadata = {
            "accepted_base_sha": args.accepted_base,
            "pr_base_sha": args.pr_base,
            "head_sha": args.head,
            "stacked_phase": args.phase,
            "pr_number": None,
        }

    payload = audit(
        metadata["accepted_base_sha"],
        metadata["head_sha"],
        pr_base=metadata["pr_base_sha"],
        phase_number=metadata["stacked_phase"],
    )
    payload["pr_number"] = metadata.get("pr_number")
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(
        "Stacked Phase history audit passed: "
        f"phase {payload['stacked_phase']}, "
        f"{payload['audited_commit_count']} commits, "
        "0 merges, 0 unexpected."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"Phase history audit failed: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1) from exc
