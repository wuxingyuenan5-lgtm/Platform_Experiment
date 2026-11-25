from app.research_history_coverage import series_coverage


def test_daily_holes_and_invalid_values_are_distinct_from_explicit_nulls():
    result = series_coverage(dict(frequency="daily", observations=[
        dict(date="2026-11-01", value="1"), dict(date="2026-11-03", value=None),
        dict(date="2026-11-03", value="NaN"), dict(date="not-a-date", value="3")]), calendar_days=True)
    assert result["missingDates"] == ["2026-11-02"]
    assert result["explicitNullDates"] == ["2026-11-03"]
    assert result["duplicateDates"] == 1
    assert result["invalidDates"] == ["2026-11-03", "not-a-date"]


def test_business_weekends_and_disclosure_schedules_are_not_missing_days():
    for frequency in ("daily", "daily_business_day", "monthly", "event"):
        result = series_coverage(dict(frequency=frequency, observations=[
            dict(date="2026-10-30", value="1"), dict(date="2026-11-02", value="2")]))
        assert result["missingDates"] == []
        assert result["longGapCandidates"] == []
    result = series_coverage(dict(frequency="monthly", observations=[
        dict(date="2026-01-01", value="1"), dict(date="2026-05-01", value="2")]))
    assert len(result["longGapCandidates"]) == 1
    assert result["missingDates"] == []


def test_coverage_isolates_bad_domain_and_reports_native_session_holes(monkeypatch):
    from datetime import datetime, UTC
    from app import research_history_coverage as coverage
    def read(path):
        if path == 'public/v1/macro/dashboard.json':
            raise ValueError('invalid file')
        if path.endswith('us-session-prices.json'):
            return dict(status='partial', rows=[dict(date='2026-01-30T21:00:00+00:00',
                        ndx=None, btc='50000', xau='2000')])
        return dict(groups={'test': [dict(seriesId='test', observations=[dict(date='2026-11-06', value='1')])]})
    monkeypatch.setattr(coverage, 'read_local_json', read)
    monkeypatch.setattr(coverage, 'local_json_revision', lambda _: None)
    result = {r['key']: r for r in coverage.research_history_checks(datetime.now(UTC))}
    assert result['history.coverage.macro']['status'] == 'error'
    assert result['history.coverage.crypto']['status'] == 'healthy'
    assert result['crypto.coverage.session_prices']['status'] == 'warning'
    assert result['crypto.coverage.session_prices']['evidence']['missingEndpoints'] == {
        'ndx': ['2026-01-30T21:00:00+00:00'], 'btc': [], 'xau': []}
