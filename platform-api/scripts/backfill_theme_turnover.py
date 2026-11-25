import json,hashlib
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import UTC,datetime
from decimal import Decimal
import httpx
from app.research_equity_catalog import CN_THEME_CODES
from app.research_a_share_repository import read_stored_stock_histories,connection,write_history_points,start_refresh
from app.research_local_data import write_local_json,hedge_board_data_root

def main():
 h=read_stored_stock_histories(list(CN_THEME_CODES)); days={str(p.observed_at) for ps in h.values() for p in ps}
 with connection() as db:
  known={(r[0],r[1]) for r in db.execute("SELECT observed_at,entity_code FROM research_a_share_history WHERE dataset IN ('theme_amount','theme_amount_public')")}
  den={r[0]:r[1] for r in db.execute("SELECT trade_date,amount_yuan FROM research_a_share_market_archive WHERE universe_key='all_a' AND quality_status<>'conflict' AND amount_yuan IS NOT NULL") if r[0] in days}
 run='public-turnover-'+datetime.now(UTC).strftime('%Y%m%dT%H%M%S')
 start_refresh(run,None)
 cache={}
 for file in (hedge_board_data_root()/'raw/research/theme-turnover').glob('*.json'):
  raw=json.loads(file.read_text(encoding='utf-8')); body=json.loads(raw['rawText']).get('data')
  if body:cache[body['code']]=(body,raw['sourceUrl'])
 def fetch(item):
  code,ps=item; missing={str(p.observed_at) for p in ps if str(p.observed_at) in den and (str(p.observed_at),code) not in known}
  if not missing:return []
  params={'secid':('1.' if code.startswith('6') else '0.')+code,'klt':101,'fqt':0,'beg':min(missing).replace('-',''),'end':max(missing).replace('-',''),'fields1':'f1,f2,f3','fields2':'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'}
  if code in cache:
   d,url=cache[code];out=[]
   for line in d['klines']:
    f=line.split(',');a=Decimal(f[6])
    if f[0] in missing and a.is_finite() and a>=0:out.append((f[0],code,{'amountYuan':str(a),'sourceUrl':url}))
   return out
  with httpx.Client(timeout=30) as client:
   r=client.get('https://push2his.eastmoney.com/api/qt/stock/kline/get',params=params);r.raise_for_status();d=r.json()['data']
  if not d or d['code']!=code:raise ValueError('identity')
  out=[]
  for line in d['klines']:
   f=line.split(',');a=Decimal(f[6])
   if f[0] in missing and a.is_finite() and a>=0:out.append((f[0],code,{'amountYuan':str(a),'sourceUrl':str(r.url)}))
  digest=hashlib.sha256(r.content).hexdigest();write_local_json('raw/research/theme-turnover/'+digest+'.json',{'sourceUrl':str(r.url),'observedAt':datetime.now(UTC).isoformat(),'rawText':r.text})
  return out
 count=0;fail=[]
 with ThreadPoolExecutor(max_workers=4) as pool:
  fs={pool.submit(fetch,item):item[0] for item in h.items()}
  for future in as_completed(fs):
   try:
    points=future.result();write_history_points(run,'theme_amount_public',points,source='Eastmoney unadjusted daily turnover');count+=len(points)
   except Exception as e:fail.append({'code':fs[future],'error':type(e).__name__})
 points=[(d,'__market__',{'amountYuan':v,'definition':'archived-all-A-turnover'}) for d,v in den.items() if (d,'__market__') not in known]
 write_history_points(run,'theme_amount_public',points,source='Existing all-A archive')
 
 with connection() as db:db.execute("UPDATE research_a_share_refresh_runs SET status='partial',target_trade_date=NULL,finished_at=? WHERE run_id=?",(datetime.now(UTC).isoformat(),run))
 report={'observations':count,'denominators':len(points),'failures':fail,'start':min(days),'end':max(days),'choiceRequests':0};write_local_json('research/theme-turnover-backfill/latest.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
