#!/usr/bin/env python3
"""One-shot mechanical extraction for Research provider normalization helpers."""

from __future__ import annotations

from pathlib import Path


PROVIDER_PATH = Path("platform-api/app/research_providers.py")
NORMALIZATION_IMPORT = """from app.research_provider_normalization import as_date as _date
from app.research_provider_normalization import as_decimal as _decimal
from app.research_provider_normalization import as_non_negative_integer as _integer
from app.research_provider_normalization import closest_prior_close as _closest_prior
from app.research_provider_normalization import first_present as _pick
from app.research_provider_normalization import frame_records as _records
from app.research_provider_normalization import percentage_change as _pct_change
from app.research_provider_normalization import trend_marker as _trend
"""


def main() -> None:
    text = PROVIDER_PATH.read_text(encoding="utf-8")
    if NORMALIZATION_IMPORT in text and "def _decimal(" not in text:
        print("Research normalization extraction is already applied.")
        return

    text = text.replace(
        "from decimal import Decimal, InvalidOperation\n",
        "from decimal import Decimal\n",
        1,
    )
    schema_end = "    ShortTermEmotionSnapshot,\n)\n\nUSER_AGENT ="
    if schema_end not in text:
        raise SystemExit("research_data_schemas import boundary was not found")
    text = text.replace(
        schema_end,
        "    ShortTermEmotionSnapshot,\n)\n" + NORMALIZATION_IMPORT + "\nUSER_AGENT =",
        1,
    )

    helper_start = text.find("\ndef _decimal(value: Any) -> Decimal | None:\n")
    provider_start = text.find("\n\nclass FreeResearchProvider:", helper_start)
    if helper_start < 0 or provider_start < 0:
        raise SystemExit("provider normalization helper block was not found")
    text = text[:helper_start] + text[provider_start:]

    if "InvalidOperation" in text or "def _decimal(" in text:
        raise SystemExit("provider helper extraction left duplicate normalization code")
    PROVIDER_PATH.write_text(text, encoding="utf-8")
    print("Research provider normalization helpers extracted.")


if __name__ == "__main__":
    main()
