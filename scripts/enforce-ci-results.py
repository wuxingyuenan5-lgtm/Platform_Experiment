#!/usr/bin/env python3
"""Fail a CI aggregation step unless every named upstream step succeeded."""

from __future__ import annotations

import argparse


def parse_result(value: str) -> tuple[str, str]:
    name, separator, outcome = value.partition("=")
    if not separator or not name or not outcome:
        raise argparse.ArgumentTypeError(
            f"expected NAME=OUTCOME, received {value!r}"
        )
    return name, outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=parse_result)
    args = parser.parse_args()

    failures = {name: outcome for name, outcome in args.results if outcome != "success"}
    if failures:
        formatted = ", ".join(f"{name}={outcome}" for name, outcome in failures.items())
        parser.error(f"upstream CI steps did not succeed: {formatted}")

    print(
        "CI enforcement passed: "
        + ", ".join(name for name, _outcome in args.results)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
