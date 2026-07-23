from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"marker not found in {path}: {old[:100]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


path = "platform-backend/tests/test_ops_observability.py"
file = Path(path)
text = file.read_text(encoding="utf-8")
text = text.replace(
    'assert batch.json()["status"] == "manual_intervention"',
    'assert batch.json()["status"] == "risk_unresolved"',
)
text = text.replace(
    'assert body["resultUnknownOrderCount"] == 1',
    'assert body["resultUnknownOrderCount"] == 2',
)
file.write_text(text, encoding="utf-8")

replace_once(
    "platform-backend/app/phase4_risk.py",
    '''        rows = db.execute(
            "SELECT base_exposure, average_fill_price FROM execution_batch_leg_metrics WHERE batch_id = ?",
            (batch_id,),
        ).fetchall()
''',
    '''        rows = db.execute(
            """
            SELECT base_exposure, average_fill_price
            FROM execution_batch_leg_metrics
            WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchall()
''',
)
replace_once(
    "platform-backend/app/phase4_risk.py",
    '''            UPDATE execution_batch_risk_profiles
            SET risk_state = ?, residual_notional = ?, disposition_status = ?, kill_switch_engaged = ?
            WHERE batch_id = ?
''',
    '''            UPDATE execution_batch_risk_profiles
            SET risk_state = ?, residual_notional = ?,
                disposition_status = ?, kill_switch_engaged = ?
            WHERE batch_id = ?
''',
)
replace_once(
    "platform-backend/tests/test_phase4_risk.py",
    '''                        INSERT INTO orders (id, command_id, account_id, instrument_id, symbol, side, order_type, quantity, price, status, created_at, updated_at)
                        VALUES ('o1', 'c1', ?, ?, ?, ?, ?, ?, NULL, 'filled', '2026-07-23T00:00:00+00:00', '2026-07-23T00:00:00+00:00')
''',
    '''                        INSERT INTO orders (
                            id, command_id, account_id, instrument_id, symbol,
                            side, order_type, quantity, price, status,
                            created_at, updated_at
                        ) VALUES (
                            'o1', 'c1', ?, ?, ?, ?, ?, ?, NULL, 'filled',
                            '2026-07-23T00:00:00+00:00',
                            '2026-07-23T00:00:00+00:00'
                        )
''',
)
replace_once(
    "platform-backend/tests/test_phase4_risk.py",
    '''                        INSERT INTO fills (id, order_id, account_id, instrument_id, side, quantity, price, occurred_at)
                        VALUES ('f1', 'o1', ?, ?, ?, '0.01', '100', '2026-07-23T00:00:00+00:00')
''',
    '''                        INSERT INTO fills (
                            id, order_id, account_id, instrument_id,
                            side, quantity, price, occurred_at
                        ) VALUES (
                            'f1', 'o1', ?, ?, ?, '0.01', '100',
                            '2026-07-23T00:00:00+00:00'
                        )
''',
)
