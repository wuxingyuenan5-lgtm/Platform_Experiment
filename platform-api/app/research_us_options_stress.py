"""Read a same-session snapshot of the producer's U.S. options observations."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError

SERIES = {
    'vix': 'cboe_vix_close',
    'vix9d': 'cboe_vix9d_close',
    'vix3m': 'cboe_vix3m_close',
    'vixeq': 'cboe_vixeq_close',
    'vvix': 'cboe_vvix_close',
    'skew': 'cboe_skew_close',
    'dspx': 'dspx',
    'nvda': 'nasdaq_nvda_close',
    'pcEquity': 'cboe_pc_equity',
    'pcTotal': 'cboe_pc_total',
    'pcIndex': 'cboe_pc_index',
}
RATIOS = {'vixeqVix': ('vixeq', 'vix'), 'vixVxv': ('vix', 'vix3m'), 'vix9dVix': ('vix9d', 'vix')}
EXPOSURES = ('spxGex', 'dealerGamma', 'netDelta')


def _series(series_id: str) -> dict:
    try:
        return read_local_json(f'public/v1/macro/series/{series_id}.json')
    except ResearchProviderError:
        return {}


def _reading(series: dict, day: str) -> Decimal | None:
    matches = [row.get('value') for row in series.get('observations', []) if row.get('date') == day]
    if len(matches) != 1:
        return None
    try:
        value = Decimal(str(matches[0]))
    except InvalidOperation:
        return None
    return value if value.is_finite() and value >= 0 else None


def read_options_stress() -> dict[str, object]:
    payloads = {key: _series(series_id) for key, series_id in SERIES.items()}
    today = datetime.now(ZoneInfo('America/New_York')).date()
    dates = [series.get('observationDate') for series in payloads.values()]
    day = max((date for date in dates if isinstance(date, str) and date <= today.isoformat()), default=None)
    readings = {key: _reading(series, day) if day else None for key, series in payloads.items()}
    ratios = {}
    for key, (numerator_key, denominator_key) in RATIOS.items():
        numerator, denominator = readings[numerator_key], readings[denominator_key]
        ratios[key] = numerator / denominator if numerator is not None and denominator else None

    term = {key: readings.pop(key) for key in ('vix9d', 'vix3m')}
    readings.pop('vixeq')
    values = {**readings, **ratios, **dict.fromkeys(EXPOSURES)}
    pending = [key for key, series in payloads.items()
               if day and (series.get('observationDate') != day or series.get('status') != 'ready')]
    return {
        'observationDate': day,
        'status': ('no_data' if not day or not any(value is not None for value in values.values())
                   else 'stale' if (today - datetime.fromisoformat(day).date()).days > 7 else 'partial'),
        'pendingSeries': pending,
        'readings': {key: str(value) if value is not None else None for key, value in values.items()},
        'term': {key: str(value) if value is not None else None for key, value in term.items()},
    }
