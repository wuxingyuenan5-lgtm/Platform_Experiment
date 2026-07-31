#!/usr/bin/env python3
"""Apply the one-shot member-holding valuation extraction."""

from pathlib import Path

SERVICE = Path("platform-api/app/member_holding_service.py")
PYPROJECT = Path("platform-api/pyproject.toml")
ARCHITECTURE = Path("platform-api/tests/test_member_holding_architecture.py")
VALUATION_IMPORT = """from app.member_holding_valuation import (
    HoldingValuationError,
    build_holding_response,
)
"""
IMPORT_MARKER = "from app.member_holding_repository import (\n"
FUNCTION_START = "def _parse_aware(value: str, *, field: str) -> datetime:\n"
FUNCTION_END = "def _list_response("
VALUATION_TYPE_LINE = '  "app/member_holding_valuation.py",\n'
TYPE_MARKER = '  "app/member_holding_service.py",\n'
ARCHITECTURE_LINE = '    "member_holding_valuation.py",\n'
ARCHITECTURE_MARKER = '    "member_holding_service.py",\n'


def main() -> None:
    service = SERVICE.read_text(encoding="utf-8")
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    architecture = ARCHITECTURE.read_text(encoding="utf-8")

    if VALUATION_IMPORT not in service:
        if IMPORT_MARKER not in service:
            raise SystemExit("Member-holding repository import boundary was not found")
        service = service.replace(IMPORT_MARKER, VALUATION_IMPORT + IMPORT_MARKER, 1)

    if FUNCTION_START in service:
        start = service.index(FUNCTION_START)
        end = service.index(FUNCTION_END, start)
        replacement = """def _holding_response(
    db: sqlite3.Connection,
    holding: MemberHoldingRecord,
    *,
    current: datetime,
) -> MemberHoldingResponse:
    fund = get_fund(db, holding.fund_id)
    if fund is None:
        raise MemberHoldingServiceError(503, "fund_unavailable", "Holding fund is unavailable")
    nav = get_latest_available_nav(db, holding.fund_id)
    try:
        return build_holding_response(
            fund=fund,
            holding=holding,
            nav=nav,
            current=current,
            stale_after_hours=get_settings().fund_nav_stale_after_hours,
        )
    except HoldingValuationError as exc:
        raise MemberHoldingServiceError(503, exc.code, exc.detail) from exc


"""
        service = service[:start] + replacement + service[end:]

    for line in (
        "    calculate_holding,\n",
        "    HoldingStatus,\n",
        "    NavStatus,\n",
    ):
        service = service.replace(line, "", 1)

    if VALUATION_TYPE_LINE not in pyproject:
        if TYPE_MARKER not in pyproject:
            raise SystemExit("Member-holding Pyright boundary was not found")
        pyproject = pyproject.replace(TYPE_MARKER, VALUATION_TYPE_LINE + TYPE_MARKER, 1)

    if ARCHITECTURE_LINE not in architecture:
        if ARCHITECTURE_MARKER not in architecture:
            raise SystemExit("Member-holding architecture list boundary was not found")
        architecture = architecture.replace(
            ARCHITECTURE_MARKER,
            ARCHITECTURE_MARKER + ARCHITECTURE_LINE,
            1,
        )

    required = (
        VALUATION_IMPORT.strip(),
        "return build_holding_response(",
        "except HoldingValuationError as exc:",
        "def put_member_holding(",
        "def put_fund_nav(",
        'db.execute("BEGIN IMMEDIATE")',
        "assert_recent_reauthentication",
        "insert_audit_event",
    )
    if any(value not in service for value in required):
        raise SystemExit("Member-holding service contract moved unexpectedly")

    forbidden = (
        "def _parse_aware",
        "calculate_holding(",
        'nav_status: NavStatus = "unavailable"',
    )
    if any(value in service for value in forbidden):
        raise SystemExit("Member-holding service retained valuation implementation details")

    SERVICE.write_text(service, encoding="utf-8")
    PYPROJECT.write_text(pyproject, encoding="utf-8")
    ARCHITECTURE.write_text(architecture, encoding="utf-8")


if __name__ == "__main__":
    main()
