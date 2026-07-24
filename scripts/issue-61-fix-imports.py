from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise SystemExit(f"expected one import block in {path}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


replace_once(
    ROOT / "platform-backend/app/financial_projection_service.py",
    '''from app.financial_fact_normalization import decimal_text, utc_iso
from app.position_math import calculate_position_update
from app.financial_fact_schemas import (
    TRADE_FACT_TYPES,
    FinancialProjectionRebuildResponse,
    FormalNavSnapshotResponse,
)
''',
    '''from app.financial_fact_normalization import decimal_text, utc_iso
from app.financial_fact_schemas import (
    TRADE_FACT_TYPES,
    FinancialProjectionRebuildResponse,
    FormalNavSnapshotResponse,
)
from app.position_math import calculate_position_update
''',
)

replace_once(
    ROOT / "platform-backend/tests/test_architecture_financial_projection_service.py",
    '''from app import financial_facts
from app import financial_projection_service as service
from app import position_math
''',
    '''from app import financial_facts, position_math
from app import financial_projection_service as service
''',
)

replace_once(
    ROOT / "platform-backend/tests/test_architecture_position_math.py",
    '''from app import financial_facts
from app import financial_projection_service as formal_projection
from app import position_math
from app import trading
''',
    '''from app import financial_facts, position_math, trading
from app import financial_projection_service as formal_projection
''',
)

Path(__file__).unlink()
workflow = ROOT / ".github/workflows/issue-61-fix-imports.yml"
if workflow.exists():
    workflow.unlink()
