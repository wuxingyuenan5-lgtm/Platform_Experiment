"""Run a true no-new-ESLint-debt gate for changed frontend source.

New frontend files must be warning-free. Modified inherited files are compared
against their merge-base content under the current ESLint configuration:
existing diagnostics may decrease, but no rule/severity count may increase and
no diagnostic may remain on a line touched by the change. Exact-content renames
remain excluded because directory migrations have separate structure gates.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "platform-web"
SOURCE_PREFIXES = ("platform-web/src/", "platform-web/mock/")
SOURCE_SUFFIXES = (".js", ".jsx", ".ts", ".tsx", ".vue")
ZERO_SHA = "0" * 40
DIAGNOSTIC_PATH = Path("/tmp/frontend-eslint.log")


class FrontendDebtError(RuntimeError):
    """The changed-file lint gate could not determine or validate its scope."""


class FrontendChange(NamedTuple):
    status: str
    base_path: str | None
    current_path: str


class EslintDiagnostic(NamedTuple):
    rule_id: str
    severity: int
    line: int
    end_line: int
    message: str
    fatal: bool


def _normalize_path(raw_path: str) -> str:
    return raw_path.replace("\\", "/").lstrip("./")


def _is_frontend_source(path: str) -> bool:
    return path.startswith(SOURCE_PREFIXES) and path.endswith(SOURCE_SUFFIXES)


def select_frontend_files(paths: list[str]) -> list[str]:
    """Compatibility helper returning current frontend-relative paths."""
    selected: list[str] = []
    for raw_path in paths:
        normalized = _normalize_path(raw_path)
        if not _is_frontend_source(normalized):
            continue
        path = ROOT / normalized
        if path.is_file():
            selected.append(str(path.relative_to(FRONTEND_ROOT)).replace("\\", "/"))
    return sorted(set(selected))


def select_frontend_changes(changes: list[FrontendChange]) -> list[FrontendChange]:
    selected: dict[str, FrontendChange] = {}
    for change in changes:
        current_path = _normalize_path(change.current_path)
        if not _is_frontend_source(current_path):
            continue
        path = ROOT / current_path
        if not path.is_file():
            continue
        base_path = _normalize_path(change.base_path) if change.base_path else None
        selected[current_path] = FrontendChange(
            status=change.status,
            base_path=base_path,
            current_path=current_path,
        )
    return [selected[path] for path in sorted(selected)]


def read_event() -> dict[str, Any]:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        return {}
    path = Path(event_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def event_base_sha(event: dict[str, Any]) -> tuple[str | None, bool]:
    pull_request = event.get("pull_request")
    if isinstance(pull_request, dict):
        base = pull_request.get("base")
        if isinstance(base, dict) and isinstance(base.get("sha"), str):
            return base["sha"], True

    before = event.get("before")
    if isinstance(before, str) and before != ZERO_SHA:
        return before, False
    return None, False


def parse_changed_files(output: str) -> list[FrontendChange]:
    """Parse git name-status records while preserving modified rename origins."""
    changes: list[FrontendChange] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split("\t")
        status = fields[0]
        if status == "R100":
            continue
        if status.startswith("R"):
            if len(fields) != 3:
                raise FrontendDebtError(f"unexpected rename record: {raw_line}")
            changes.append(
                FrontendChange(
                    status=status,
                    base_path=fields[1],
                    current_path=fields[2],
                )
            )
            continue
        if len(fields) != 2:
            raise FrontendDebtError(f"unexpected changed-file record: {raw_line}")
        current_path = fields[1]
        changes.append(
            FrontendChange(
                status=status,
                base_path=None if status.startswith("A") else current_path,
                current_path=current_path,
            )
        )
    return changes


def parse_changed_paths(output: str) -> list[str]:
    """Compatibility helper returning destinations requiring validation."""
    return [change.current_path for change in parse_changed_files(output)]


def changed_frontend_files(base_sha: str, *, merge_base: bool) -> list[FrontendChange]:
    separator = "..." if merge_base else ".."
    command = [
        "git",
        "-c",
        "core.quotepath=false",
        "diff",
        "--name-status",
        "--find-renames=50%",
        "--diff-filter=ACMR",
        f"{base_sha}{separator}HEAD",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise FrontendDebtError(result.stderr.strip() or "git diff failed")
    return parse_changed_files(result.stdout)


def changed_paths(base_sha: str, *, merge_base: bool) -> list[str]:
    """Compatibility helper for callers that only need destination paths."""
    return [
        change.current_path
        for change in changed_frontend_files(base_sha, merge_base=merge_base)
    ]


def read_base_blob(base_sha: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{base_sha}:{path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise FrontendDebtError(detail or f"unable to read {path} at {base_sha}")
    return result.stdout


def _parse_eslint_output(output: str, relative_path: str) -> list[EslintDiagnostic]:
    try:
        payload = json.loads(output or "[]")
    except json.JSONDecodeError as exc:
        raise FrontendDebtError(
            f"ESLint returned non-JSON output for {relative_path}: {output[:500]}"
        ) from exc
    if not isinstance(payload, list):
        raise FrontendDebtError(f"unexpected ESLint payload for {relative_path}")
    messages: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict) and isinstance(item.get("messages"), list):
            messages.extend(
                message for message in item["messages"] if isinstance(message, dict)
            )
    diagnostics: list[EslintDiagnostic] = []
    for message in messages:
        severity = int(message.get("severity") or 0)
        if severity <= 0:
            continue
        line = max(1, int(message.get("line") or 1))
        end_line = max(line, int(message.get("endLine") or line))
        fatal = bool(message.get("fatal"))
        rule_id = str(
            message.get("ruleId") or ("<fatal>" if fatal else "<unclassified>")
        )
        diagnostics.append(
            EslintDiagnostic(
                rule_id=rule_id,
                severity=severity,
                line=line,
                end_line=end_line,
                message=str(message.get("message") or ""),
                fatal=fatal,
            )
        )
    return diagnostics


def run_eslint_json(relative_path: str) -> list[EslintDiagnostic]:
    result = subprocess.run(
        [
            "pnpm",
            "exec",
            "eslint",
            "--format",
            "json",
            "--no-error-on-unmatched-pattern",
            relative_path,
        ],
        cwd=FRONTEND_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        detail = f"{result.stdout}{result.stderr}".strip()
        raise FrontendDebtError(
            detail or f"ESLint failed to execute for {relative_path}"
        )
    return _parse_eslint_output(result.stdout, relative_path)


def changed_current_lines(base_text: str, current_text: str) -> set[int]:
    """Return changed current lines plus one-line formatting boundaries."""
    base_lines = base_text.splitlines()
    current_lines = current_text.splitlines()
    touched: set[int] = set()
    matcher = difflib.SequenceMatcher(
        a=base_lines,
        b=current_lines,
        autojunk=False,
    )
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        start = max(0, j1 - 1)
        stop = min(len(current_lines), max(j2, j1 + 1) + 1)
        touched.update(range(start + 1, stop + 1))
    return touched


def diagnostic_counts(
    diagnostics: list[EslintDiagnostic],
) -> Counter[tuple[int, str]]:
    return Counter((item.severity, item.rule_id) for item in diagnostics)


def _diagnostic_intersects(
    diagnostic: EslintDiagnostic,
    touched_lines: set[int],
) -> bool:
    return any(
        line in touched_lines
        for line in range(diagnostic.line, diagnostic.end_line + 1)
    )


def compare_diagnostics(
    *,
    relative_path: str,
    base: list[EslintDiagnostic] | None,
    current: list[EslintDiagnostic],
    touched_lines: set[int],
) -> list[str]:
    issues: list[str] = []
    if base is None:
        for item in current:
            issues.append(
                f"{relative_path}:{item.line} new file must be clean: "
                f"{item.rule_id} {item.message}"
            )
        return issues

    base_counts = diagnostic_counts(base)
    current_counts = diagnostic_counts(current)
    for key, current_count in sorted(current_counts.items()):
        base_count = base_counts.get(key, 0)
        if current_count > base_count:
            severity, rule_id = key
            issues.append(
                f"{relative_path} increased severity {severity} rule {rule_id}: "
                f"{base_count} -> {current_count}"
            )

    for item in current:
        if item.fatal:
            issues.append(
                f"{relative_path}:{item.line} contains a fatal ESLint diagnostic: "
                f"{item.message}"
            )
        elif _diagnostic_intersects(item, touched_lines):
            issues.append(
                f"{relative_path}:{item.line} touched code is not clean: "
                f"{item.rule_id} {item.message}"
            )
    return sorted(set(issues))


def _lint_base_version(
    *,
    relative_path: str,
    absolute_path: Path,
    base_content: bytes,
) -> list[EslintDiagnostic]:
    current_content = absolute_path.read_bytes()
    try:
        absolute_path.write_bytes(base_content)
        return run_eslint_json(relative_path)
    finally:
        absolute_path.write_bytes(current_content)


def _write_diagnostic_report(lines: list[str]) -> None:
    if not lines:
        return
    with DIAGNOSTIC_PATH.open("a", encoding="utf-8") as diagnostic:
        diagnostic.write("\n".join(lines))
        diagnostic.write("\n")


def run_no_new_debt(
    changes: list[FrontendChange],
    *,
    base_sha: str,
) -> int:
    if not changes:
        print("Frontend no-new-debt check passed: no changed source content")
        return 0

    print("Frontend no-new-debt files:")
    for change in changes:
        base_label = change.base_path or "<new>"
        print(f"- {change.current_path} (base: {base_label})")

    failures: list[str] = []
    report: list[str] = []
    for change in changes:
        absolute_path = ROOT / change.current_path
        relative_path = str(absolute_path.relative_to(FRONTEND_ROOT)).replace(
            "\\", "/"
        )
        current_content = absolute_path.read_bytes()
        current = run_eslint_json(relative_path)

        base: list[EslintDiagnostic] | None = None
        touched_lines = set(range(1, len(current_content.splitlines()) + 1))
        if change.base_path is not None:
            base_content = read_base_blob(base_sha, change.base_path)
            base = _lint_base_version(
                relative_path=relative_path,
                absolute_path=absolute_path,
                base_content=base_content,
            )
            touched_lines = changed_current_lines(
                base_content.decode("utf-8-sig"),
                current_content.decode("utf-8-sig"),
            )

        issues = compare_diagnostics(
            relative_path=relative_path,
            base=base,
            current=current,
            touched_lines=touched_lines,
        )
        base_count = 0 if base is None else len(base)
        report.append(
            f"{relative_path}: base={base_count}, current={len(current)}, "
            f"touched_lines={len(touched_lines)}, issues={len(issues)}"
        )
        failures.extend(issues)

    _write_diagnostic_report([*report, *failures])
    for line in report:
        print(line)
    if failures:
        print("Frontend no-new-debt check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("Frontend no-new-debt check passed: no diagnostic debt was added")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base",
        help="Base commit SHA. GitHub event metadata is used by default.",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use base..HEAD instead of merge-base comparison.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    event = read_event()
    event_base, event_uses_merge_base = event_base_sha(event)
    base_sha = args.base or event_base
    merge_base = False if args.direct else event_uses_merge_base
    if base_sha is None:
        print(
            "Frontend no-new-debt check skipped: no base SHA outside GitHub CI",
            file=sys.stderr,
        )
        return 0

    try:
        changes = select_frontend_changes(
            changed_frontend_files(base_sha, merge_base=merge_base)
        )
        return run_no_new_debt(changes, base_sha=base_sha)
    except (FrontendDebtError, OSError, UnicodeError) as exc:
        print(f"Frontend no-new-debt check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
