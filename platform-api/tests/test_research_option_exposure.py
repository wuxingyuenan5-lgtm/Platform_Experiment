from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError
from app.research_option_exposure import OptionExposureSnapshot
from app.research_provider_macro_dashboard import MacroDashboardResponse

pytestmark = pytest.mark.unit


def snapshot():
    return OptionExposureSnapshot.model_validate(dict(market='deribit', status='ready', source='Deribit', sourceUrl='https://www.deribit.com',
        collectedAt='2026-10-11T05:00:00+00:00', asOf='2026-10-11T05:00:00+00:00', underlyingPrice='80000',
        model='black76_forward_gamma', oiUnit='BTC', totalContracts=1, excludedContracts=0, totalOpenInterest='2.123456789', includedOpenInterest='2.123456789',
        legs=[dict(symbol='BTC-test', expiry='2026-10-20T08:00:00+00:00', strike='80000', side='call', openInterest='2.123456789', gamma='0.00001', underlyingPrice='80000', multiplier='1', exposureUsd='1359.01234496')]))


def test_decimal_and_freshness():
    item = snapshot()
    assert str(item.legs[0].open_interest) == '2.123456789'
    item.apply_freshness(datetime(2026,10,11,5,21,tzinfo=timezone.utc))
    assert item.status == 'stale'
    assert 'snapshot_refresh_due' in item.quality_flags


def test_inconsistent_coverage_and_naive_time_rejected():
    data = snapshot().model_dump(mode='json', by_alias=True)
    data['includedOpenInterest'] = '3'
    with pytest.raises(ValidationError): OptionExposureSnapshot.model_validate(data)
    data = snapshot().model_dump(mode='json', by_alias=True)
    data['collectedAt'] = '2026-10-11T05:00:00'
    with pytest.raises(ValidationError): OptionExposureSnapshot.model_validate(data)


def test_dashboard_failure_marks_option_snapshot_stale():
    d = MacroDashboardResponse(status='ready', as_of='2026-10-11', groups={}, option_exposure={'deribit': snapshot()})
    stale = d.stale_copy()
    assert stale.option_exposure['deribit'].status == 'stale'
    assert d.option_exposure['deribit'].status == 'ready'
