from datetime import UTC, datetime
import json

from app import research_crypto_coverage as module


def test_crypto_coverage_distinguishes_business_days_and_reports_iv_calendar_gaps(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'SERIES', {'fixture': ['daily', 'business']})
    monkeypatch.setattr(module, 'hedge_board_data_root', lambda: tmp_path)
    for name, frequency in [('daily', 'daily'), ('business', 'daily_business_day')]:
        path = tmp_path / f'public/v1/crypto/series/{name}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'frequency': frequency, 'status': 'ready', 'observations': [
            {'date': '2026-11-06', 'value': 1}, {'date': '2026-11-09', 'value': 2}]}))
    monkeypatch.setattr(module, 'read_iv_snapshot_dates', lambda: [
        {'entity_code': tenor, 'observed_at': day} for tenor in ['1M','3M','6M','1Y']
        for day in ['2026-11-06','2026-11-08']])
    result = module.crypto_coverage_checks(datetime.now(UTC))
    gaps = result[1]['evidence']['gaps']
    assert [row['series'] for row in gaps] == ['daily']
    assert gaps[0]['missingDates'] == ['2026-11-07', '2026-11-08']
    assert result[2]['evidence']['records'][0]['missingDates'] == ['2026-11-07']
