from datetime import datetime, UTC

import pytest

from app import research_provider_overseas as provider


def test_hourly_dvol_uses_close_and_combines_reverse_pages(monkeypatch):
    ts = int(datetime.now(UTC).timestamp() * 1000) - 86400000
    pages = [
        {'data': [[ts, 40, 44, 39, 42.123456]], 'continuation': ts - 1},
        {'data': [[ts - 3600000, 39, 44, 38, 41.123456]], 'continuation': None},
    ]
    monkeypatch.setattr(provider, '_deribit_get', lambda *args: {'result': pages.pop(0)})
    result = provider.fetch_deribit_dvol()
    assert result['latest'] == 42.123456
    assert [r['value'] for r in result['history']] == [41.123456, 42.123456]


def test_hourly_dvol_stuck_cursor_fails(monkeypatch):
    monkeypatch.setattr(provider, '_deribit_get', lambda method, params: {
        'result': {'data': [], 'continuation': params['end_timestamp']}})
    with pytest.raises(ValueError, match='advance'):
        provider.fetch_deribit_dvol()
