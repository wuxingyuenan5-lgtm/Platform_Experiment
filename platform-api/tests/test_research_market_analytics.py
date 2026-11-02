import math
from collections import deque
from datetime import date, timedelta
from decimal import Decimal
from statistics import stdev

import pytest

from app.research_history_risk import analyze_prices, annual_volatility
from app.research_liquidity_lens import aligned_quantity, build_lens, values


def points(prices):
    return [{"date": (date(2026,1,1)+timedelta(days=i)).isoformat(), "close": p} for i,p in enumerate(prices)]


def test_drawdown_episode_recovery_and_calendar_duration():
    result=analyze_prices(points([100,120,90,80,120,130]),2026)
    episode=result['episodes'][0]
    assert episode['peakDate']=='2026-01-02'
    assert episode['troughDate']=='2026-01-04'
    assert episode['recoveryDate']=='2026-01-05'
    assert episode['daysUnderwater']==3
    assert abs(episode['depth']-Decimal('-33.33333333333333333333333333'))<Decimal('1e-24')
    assert result['summary']['drawdown']==0


def test_unrecovered_episode_keeps_actual_depth():
    result=analyze_prices(points([100,110,80,90]),2026)
    assert result['episodes'][0]['recoveryDate'] is None
    assert result['episodes'][0]['daysUnderwater']==2
    assert result['summary']['maxDrawdown']<result['summary']['drawdown']


def test_annual_drawdown_includes_previous_december_close():
    result=analyze_prices([{'date':'2023-12-29','close':100},{'date':'2024-01-02','close':90},{'date':'2024-12-31','close':110}],2026)
    assert result['annual'][0]['return'] is None
    assert result['annual'][1]['return']==10
    assert result['annual'][1]['drawdown']==-10
    assert result['annual'][1]['partial']


def test_volatility_is_sample_standard_deviation_and_annualized_once():
    window=deque([(-1)**i * (i+1)/5 for i in range(60)])
    assert annual_volatility(window)==pytest.approx(stdev(window)*math.sqrt(252),rel=1e-12)
    assert annual_volatility(deque([1.0]*20))==0
    prices=[Decimal(100)]
    for i in range(20):prices.append(prices[-1]*(Decimal('1.01') if i%2 else Decimal('.99')))
    result=analyze_prices(points(prices),2026)
    assert result['history'][19]['vol20'] is None
    assert result['history'][20]['vol20']==pytest.approx(stdev([-1,1]*10)*math.sqrt(252),rel=1e-12)


def test_invalid_and_long_gaps_do_not_become_daily_returns():
    result=analyze_prices([{'date':'2026-01-01','close':100},{'date':'2026-01-02','close':0},{'date':'2026-01-03','close':110},{'date':'2026-02-01','close':120}],2026)
    assert result['invalid']==1 and result['gaps']==1
    assert result['history'][2]['return1'] is None
    assert result['history'][3]['return1'] is None
    with pytest.raises(ValueError,match='duplicate_price_dates'):
        analyze_prices(points([100])*2,2026)


def test_five_year_annualization_uses_actual_calendar_length():
    result=analyze_prices([{'date':'2019-01-02','close':100},{'date':'2024-01-02','close':'161.051'}],2026)
    expected=(1.61051**(365.25/1826)-1)*100
    assert result['history'][-1]['rolling5y']==pytest.approx(expected,rel=1e-12)


def test_liquidity_contributions_sum_and_zero_is_valid():
    assets={'2026-09-30':Decimal(100),'2026-10-28':Decimal(105)}
    tga={'2026-09-30':Decimal(10),'2026-10-28':Decimal(18)}
    rrp={'2026-09-30':Decimal(3),'2026-10-28':Decimal(0)}
    rows=aligned_quantity(assets,tga,rrp)
    assert rows[-1]['net']==87
    assert rows[-1]['fedChange']==5 and rows[-1]['tgaEffect']==-8 and rows[-1]['rrpEffect']==3
    assert rows[-1]['netChange']==sum(rows[-1][k] for k in ['fedChange','tgaEffect','rrpEffect'])==0


def test_unit_conversion_refuses_percent_basis_point_mix():
    assert values({'unit':'usd_million','observations':[{'date':'2026-10-28','value':1000}]},'usd_million',Decimal('.001'))['2026-10-28']==1
    with pytest.raises(ValueError,match='unit_mismatch'):
        values({'unit':'percent','observations':[]},'basis_points',Decimal(1))


def test_quantity_cards_share_exact_date_and_missing_four_week_base_not_filled():
    def doc(observations):return {'unit':'usd_million','status':'ready','observations':[{'date':d,'value':v} for d,v in observations]}
    result=build_lens({'walcl':doc([('2026-10-28',1000)]),'wdtgal':doc([('2026-10-28',200)]),
                       'fed_on_rrp_million':doc([('2026-10-28',100),('2026-10-30',500)]),
                       'reserve_balances':doc([('2026-10-28',600)])})
    assert result['asOf']=='2026-10-28'
    assert result['latest']['net']==Decimal('.7')
    rrp=next(c for c in result['cards'] if c['id']=='fed_on_rrp_million')
    assert rrp['date']=='2026-10-28' and rrp['value']==Decimal('.1')
    assert result['change4w']['net'] is None
    assert result['structure'][-1]['reserves']==60


def test_one_invalid_source_keeps_other_lens_metrics_visible():
    result=build_lens({'sofr_iorb_spread':{'unit':'percent','status':'ready','observations':[{'date':'2026-10-29','value':.04}]},
                       'vix':{'unit':'index','status':'ready','observations':[{'date':'2026-10-29','value':17.2}]}})
    assert next(c for c in result['cards'] if c['id']=='sofr_iorb_spread')['status']=='error'
    assert next(c for c in result['cards'] if c['id']=='vix')['value']==Decimal('17.2')
    assert not result['history']
