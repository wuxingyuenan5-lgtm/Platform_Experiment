from __future__ import annotations

from pathlib import Path

from app import financial_fact_normalization, financial_facts

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_financial_fact_service_delegates_normalization_and_hashing() -> None:
    source = (BACKEND_ROOT / "app/financial_facts.py").read_text(encoding="utf-8")

    assert "import hashlib" not in source
    assert "MONETARY_FACT_TYPES" not in source
    assert "Trade fact currency must match instrument settlement currency" not in source
    assert "Monetary fact is incomplete" not in source
    assert "normalization.normalize_financial_fact(request, context)" in source
    assert "normalization.normalized_content_hash(normalized)" in source


def test_normalization_policy_has_no_persistence_dependency() -> None:
    source = (BACKEND_ROOT / "app/financial_fact_normalization.py").read_text(
        encoding="utf-8"
    )

    assert "financial_fact_repository" not in source
    assert "from app.database" not in source
    assert "connection()" not in source
    for anchor in (
        "class FinancialFactNormalizationContext",
        "class NormalizedFinancialFact",
        "def normalize_financial_fact",
        "def normalized_content_hash",
        "MONETARY_FACT_TYPES",
        "hashlib.sha256",
    ):
        assert anchor in source


def test_normalization_helper_compatibility_aliases_are_identity_stable() -> None:
    assert financial_facts.utc_iso is financial_fact_normalization.utc_iso
    assert financial_facts.decimal_text is financial_fact_normalization.decimal_text
