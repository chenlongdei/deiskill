#!/usr/bin/env python3
import argparse,concurrent.futures,json,os,subprocess,uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode
# Windows 中文系统默认 GBK：本脚本和它调用的 Python 工具（yt-dlp、notebooklm 等）一律用 UTF-8 输入输出
import os as _os, sys as _sys
_os.environ.setdefault("PYTHONUTF8", "1"); _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT=Path(__file__).resolve().parents[1]
def _data_dir(module):
    """数据目录：见 dei-daily-report/scripts/dei_paths.py。"""
    import sys as _sys
    env = os.environ.get('DEI_DAILY_DATA_DIR')
    if env:
        return Path(env).expanduser()
    _sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
    from dei_paths import data_dir
    return data_dir(module)
BASE=_data_dir('ai')
CST=timezone(timedelta(hours=8))
parser=argparse.ArgumentParser()
parser.add_argument('--date',help='北京时间日期 YYYY-MM-DD，查询过去七天内的一天')
args=parser.parse_args()
now=datetime.now(CST); start=now-timedelta(hours=24); end=now
if args.date:
 start=datetime.strptime(args.date,'%Y-%m-%d').replace(tzinfo=CST)
 end=start+timedelta(days=1)
 if start < now-timedelta(days=7) or end > now: parser.error('日期必须是最近七天内已结束的一天')
ua='aihot-skill/1.7.0 (+https://aihot.news/aihot-skill/)'
try:
 actor=(ROOT/'sources/aihot/.aihot-actor-id').read_text(encoding="utf-8").strip()
 parsed=uuid.UUID(actor)
 if parsed.version==4: ua+=' aihot-actor/'+str(parsed)
except (OSError,ValueError): pass

def get(url):
 result=subprocess.run(['curl','-fsSL','--max-time','35','-A',ua if url.startswith('https://aihot.news/') else 'dei-ai-brief/2.0',url],capture_output=True,text=True, encoding="utf-8", errors="replace",check=True)
 return json.loads(result.stdout)

def selected():
 url='https://aihot.news/api/v1/items'
 params={'mode':'selected','window':'7d' if args.date else '24h','by':'published','limit':50}
 pages=[]
 for i in range(4):
  data=get(url+'?'+urlencode(params)); pages.append(data)
  page=data.get('page',{})
  if not page.get('hasMore'): return {'pages':pages,'truncated':False}
  params['cursor']=page['nextCursor']
 return {'pages':pages,'truncated':True}

def builders():
 result=subprocess.run(['node',str(ROOT/'sources/follow-builders/scripts/prepare-digest.js')],capture_output=True,text=True, encoding="utf-8", errors="replace",check=True,timeout=180)
 current=json.loads(result.stdout)
 # Current feed is a replacement snapshot, not a historical archive.
 commits=get('https://api.github.com/repos/zarazhangrui/follow-builders/commits?path=feed-x.json&per_page=10')
 chosen=[]
 for c in commits:
  t=datetime.fromisoformat(c['commit']['committer']['date'].replace('Z','+00:00'))
  if start-timedelta(hours=30)<=t<=end+timedelta(hours=30): chosen.append(c)
 # Include historical snapshots for all feed types to recover overwritten entries.
 snapshots=[]
 for c in chosen:
  sha=c['sha']
  for filename,key in [('feed-x.json','x'),('feed-podcasts.json','podcasts'),('feed-blogs.json','blogs')]:
   try:
    data=get('https://raw.githubusercontent.com/zarazhangrui/follow-builders/'+sha+'/'+filename)
    snapshots.append({'commit':sha,'commitDate':c['commit']['committer']['date'],'file':filename,'data':data})
   except Exception: pass
 current['historicalSnapshots']=snapshots
 current['historyRecoveryNote']='历史快照补回中心 feed 曾采集的内容；每人条数限制、排除回复与转发及中心采集失败仍会限制覆盖。'
 return current

jobs={'aihot_selected':selected,'aihot_hot_topics':lambda:get('https://aihot.news/api/v1/hot-topics'),'builders':builders}
out={'window':{'start':start.isoformat(),'end':end.isoformat(),'timezone':'Asia/Shanghai'},'sources':{},'errors':{}}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 futures={pool.submit(fn):name for name,fn in jobs.items()}
 for future in concurrent.futures.as_completed(futures):
  name=futures[future]
  try: out['sources'][name]=future.result()
  except Exception as err: out['errors'][name]=type(err).__name__+': source unavailable'
if args.date and 'aihot_selected' in out['sources']:
 def _in_window(item):
  try: t=datetime.fromisoformat(item['publishedAt'].replace('Z','+00:00')).astimezone(CST)
  except (KeyError,ValueError): return False
  return start<=t<end
 pool=[i for p in out['sources']['aihot_selected'].get('pages',[]) for i in (p.get('items') or [])]
 out['sources']['aihot_selected_in_window']=[i for i in pool if _in_window(i)]
out['historicalCoverageNote']='Builders 已查询 GitHub 历史快照；覆盖仅限中心源曾采集内容，当前热点不是历史热点快照。' if args.date else None
raw=BASE/'sources'/start.strftime('%Y-%m-%d'); raw.mkdir(parents=True,exist_ok=True)
path=raw/(now.strftime('%Y-%m-%d_%H%M%S')+'.json')
path.write_text(json.dumps(out,ensure_ascii=False,indent=2), encoding="utf-8")
print(json.dumps({'path':str(path),'window':out['window'],'available_sources':list(out['sources']),'errors':out['errors']},ensure_ascii=False))
