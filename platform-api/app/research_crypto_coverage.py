"""Read-only coverage inventory for the crypto research entry points."""
from datetime import date, timedelta
import json
import sqlite3

from app.research_overseas_repository import read_iv_snapshot_dates
from app.research_local_data import hedge_board_data_root


SERIES = {
    '市场价格': ['binance_btc_spot', 'binance_eth_spot', 'btc_dvol'],
    '衍生品': ['binance_btc_funding', 'binance_eth_funding', 'binance_btc_open_interest', 'binance_eth_open_interest', 'bybit_usdt_borrow', 'coinbase_premium'],
    '资金面': ['stablecoin_market_cap', 'treasury_strategy', 'strc_close'],
    '链上与周期': ['btc_address_chainquery_whale', 'btc_halving_2024'],
}


def missing_dates(days):
    if not days:
        return []
    first, last = date.fromisoformat(min(days)), date.fromisoformat(max(days))
    have = set(days)
    return [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)
            if (first + timedelta(days=i)).isoformat() not in have]


def crypto_coverage_checks(now):
    from app.data_audit import check
    root = hedge_board_data_root()
    records, gaps = [], []
    try:
        for section, ids in SERIES.items():
            for sid in ids:
                relative = f'public/v1/crypto/series/{sid}.json'
                path = root / relative
                if not path.exists():
                    gaps.append({'series': sid, 'reason': 'missing_file'})
                    continue
                doc = json.loads(path.read_text(encoding='utf-8'))
                rows = doc.get('observations', [])
                days = [row['date'] for row in rows]
                flags = doc.get('qualityFlags', [])
                continuous = doc.get('frequency') in {'daily', 'daily_last_collected_snapshot'}
                missing = missing_dates(days) if continuous else []
                duplicate = len(days) - len(set(days))
                if missing or duplicate:
                    gaps.append({'series': sid, 'missingDates': missing, 'duplicates': duplicate})
                records.append({'section': section, 'series': sid, 'source': doc.get('source'),
                    'sourceUrl': doc.get('sourceUrl'), 'producer': 'platform-data / HedgeBoard-LocalData-Refresh',
                    'storage': relative, 'mirror': 'hedge_board.duckdb / observations',
                    'endpoint': '/research/crypto/dashboard-v1?groups=…',
                    'firstDate': min(days) if days else None, 'lastDate': max(days) if days else None,
                    'observations': len(rows), 'frequency': doc.get('frequency'), 'status': doc.get('status'),
                    'historyType': 'collected_snapshot' if any('history_since' in flag for flag in flags) else 'retained_source_history',
                    'publicationBoundary': 'source_calendar' if not continuous else 'calendar_day',
                    'qualityFlags': flags})
        results = [check('crypto.coverage.inventory', '加密接口与历史覆盖', '加密研究数据',
            'healthy', '按来源、采集任务、存储和消费接口登记', records=records),
            check('crypto.coverage.gaps', '加密连续序列缺口', '加密研究数据',
                'warning' if gaps else 'healthy', '缺口保留，不补零或插值' if gaps else '登记序列区间内无缺日或重复', gaps=gaps)]
        rows = read_iv_snapshot_dates()
        iv = []
        for tenor in ('1M', '3M', '6M', '1Y'):
            days = [r['observed_at'] for r in rows if r['entity_code'] == tenor]
            iv.append({'tenor': tenor, 'firstDate': min(days) if days else None,
                'lastDate': max(days) if days else None, 'snapshots': len(days), 'missingDates': missing_dates(days)})
        results.append(check('crypto.coverage.iv', '期限IV快照历史', '加密研究数据',
            'warning' if any(r['missingDates'] or not r['snapshots'] for r in iv) else 'healthy',
            '接入后日快照；无原始期权链的日期不以DVOL或插值替代', records=iv,
            source='Deribit public option book summary', producer='Platform API overseas refresh',
            storage='SQLite / research_a_share_history / crypto_iv_snapshot',
            endpoints=['/research/crypto/iv-snapshot', '/research/crypto/iv-history']))
        return results
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        return [check('crypto.coverage.inventory', '加密历史覆盖检查', '加密研究数据', 'error', '覆盖检查未完成', error=str(exc))]
