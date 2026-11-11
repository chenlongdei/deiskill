#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, json, os, re, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
import openpyxl

ROOT=Path(__file__).resolve().parent.parent; TK="https://api.tikhub.io"; DS="https://dashscope.aliyuncs.com/api/v1"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"

ASR_JOURNAL=ROOT/"data"/"asr_tasks.json"

class StopExternal(RuntimeError):
    """Credentials or balance prohibit further external calls."""

def req(url,headers=None,data=None,method=None,retries=4):
    h={"Accept":"application/json","User-Agent":UA,"Accept-Encoding":"identity"}; h.update(headers or {})
    if isinstance(data,dict): data=json.dumps(data).encode(); h.setdefault("Content-Type","application/json")
    for n in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=h,method=method),timeout=45) as r:return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401,403,402): raise StopExternal(f"HTTP {e.code} ({urllib.parse.urlparse(url).hostname})")
            if n==retries-1: raise
        except Exception:
            if n==retries-1: raise
        time.sleep(min(2**n*2,12))

def find(x,keys):
    if isinstance(x,dict):
        for k in keys:
            if x.get(k) not in (None,""): return x[k]
        for v in x.values():
            z=find(v,keys)
            if z not in (None,""): return z
    elif isinstance(x,list):
        for v in x:
            z=find(v,keys)
            if z not in (None,""): return z

def num(x):
    if isinstance(x,(int,float)) and not isinstance(x,bool): return max(0,int(x))
    m=re.search(r"([\d.]+)\s*([万亿KMB]?)",str(x or "").replace(",",""),re.I)
    return int(float(m.group(1))*{"万":1e4,"亿":1e8,"K":1e3,"M":1e6,"B":1e9}.get(m.group(2).upper(),1)) if m else 0

def norm(x): return re.sub(r"[^0-9a-z\u4e00-\u9fff]+","",str(x or "").casefold())

class TikHub:
    def __init__(self,key): self.h={"Authorization":"Bearer "+key}
    def get(self,path,p=None): return req(TK+path+("?"+urllib.parse.urlencode(p) if p else ""),self.h)
    def resolve(self,ident):
        p=self.get("/api/v1/douyin/web/handler_user_profile_v2",{"unique_id":ident}); s=str(find(p,("sec_uid","sec_user_id")) or "")
        if not s.startswith("MS4wLjAB"): raise RuntimeError("无法解析sec_uid")
        return s,str(find(p,("nickname",)) or ident),num(find(p,("follower_count","mplatform_followers_count")))
    def resolve_sec(self,sec):
        p=self.get("/api/v1/douyin/web/handler_user_profile",{"sec_user_id":sec})
        raw=find(p,("follower_count","mplatform_followers_count"))
        return sec,str(find(p,("nickname","unique_id")) or sec),num(raw) if raw not in (None,"") else None
    def from_share(self,url):
        p=self.get("/api/v1/douyin/app/v3/fetch_one_video_by_share_url",{"share_url":url}); s=str(find(p,("sec_uid","sec_user_id")) or "")
        if not s.startswith("MS4wLjAB"): raise RuntimeError("作品无法反查账号")
        return s,str(find(p,("nickname",)) or ""),num(find(p,("follower_count","mplatform_followers_count")))
    def posts(self,sec,since=0,pages=10):
        out=[]; seen=set(); cur=0
        for _ in range(pages):
            p=self.get("/api/v1/douyin/app/v3/fetch_user_post_videos",{"sec_user_id":sec,"max_cursor":cur,"count":20,"sort_type":0}); d=(p.get("data") or {}).get("data") or p.get("data") or {}; items=d.get("aweme_list") or d.get("items") or []; ts=[]
            for a in items:
                t=int(a.get("create_time") or 0); ts.append(t); vid=str(a.get("aweme_id") or a.get("id") or "")
                if not vid or vid in seen or t<since: continue
                seen.add(vid); st=a.get("statistics") or a.get("stats") or {}; mu=a.get("music") or {}
                author=a.get("author") or {}; followers_raw=author.get("follower_count") or author.get("mplatform_followers_count")
                out.append({"id":vid,"title":str(a.get("desc") or ""),"url":f"https://www.douyin.com/video/{vid}","ts":t,"publish":datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S"),"bgm":str(mu.get("title") or ""),"likes":num(st.get("digg_count")),"comments":num(st.get("comment_count")),"collects":num(st.get("collect_count")),"shares":num(st.get("share_count")),"_followers":num(followers_raw) if followers_raw not in (None,"") else None})
            nxt=d.get("max_cursor") or d.get("next_cursor")
            if not items or (since and ts and min(ts)<since) or not d.get("has_more",True) or nxt in (None,cur): break
            cur=nxt
        return sorted(out,key=lambda x:x["ts"],reverse=True)

def media(url,uid,key):
    form=urllib.parse.urlencode({"type":"dsp","uid":uid,"key":key,"url":url}).encode(); p=req("https://api.zhuceka.cn/home/api",{"Content-Type":"application/x-www-form-urlencoded"},form,"POST",2)
    if p.get("code")!=200: raise RuntimeError(str(p.get("msg") or "大圣失败"))
    d=p.get("data") or {}
    for k in ("video","video_url","url","play_url","video4k"):
        if isinstance(d.get(k),str) and d[k].startswith("http"): return d[k]
    raise RuntimeError("大圣无直链")

def submit(url,key):
    p=req(DS+"/services/audio/asr/transcription",{"Authorization":"Bearer "+key,"X-DashScope-Async":"enable"},{"model":"paraformer-v2","input":{"file_urls":[url]},"parameters":{"language_hints":["zh","en"],"timestamp_alignment_enabled":True,"disfluency_removal_enabled":True}}); tid=str((p.get("output") or {}).get("task_id") or "")
    if not tid: raise RuntimeError("百炼无task_id")
    return tid

def parse(p):
    tr=p.get("transcripts") or []; text="\n".join(str(x.get("text") or "").strip() for x in tr).strip(); ss=sum((x.get("sentences") or [] for x in tr),[])
    hook="".join(str(x.get("text") or "").strip() for x in ss if int(x.get("begin_time") or 0)<5000) or text[:60]; tail="".join(str(x.get("text") or "").strip() for x in ss[-3:]) or text[-80:]
    return text,hook,tail

def transcribe(videos,key):
    pending={}; done={}
    journal=json.loads(ASR_JOURNAL.read_text()) if ASR_JOURNAL.exists() else {}
    def save():
        ASR_JOURNAL.parent.mkdir(parents=True,exist_ok=True)
        temporary=ASR_JOURNAL.with_suffix(".tmp")
        temporary.write_text(json.dumps(journal,ensure_ascii=False,indent=2))
        temporary.replace(ASR_JOURNAL)
    for v in videos:
        try:
            prior=journal.get(v["id"],{})
            if prior.get("result"):
                done[v["id"]]=tuple(prior["result"]); continue
            tid=prior.get("task_id") or submit(v["media"],key)
            journal[v["id"]]={"task_id":tid}; save()
            pending[v["id"]]=(tid,v)
        except StopExternal: raise
        except Exception as e: v["asr_error"]=str(e)
    for _ in range(80):
        if not pending: break
        time.sleep(12); still={}
        for vid,(tid,v) in pending.items():
            try:
                p=req(DS+"/tasks/"+tid,{"Authorization":"Bearer "+key},method="GET",retries=2); o=p.get("output") or {}; s=str(o.get("task_status") or "").upper()
                if s in ("PENDING","RUNNING"): still[vid]=(tid,v)
                elif s=="SUCCEEDED":
                    done[vid]=parse(req(str(find(p,("transcription_url",)) or "")))
                    journal[vid]["result"]=done[vid]; save()
                else:
                    v["asr_error"]=str(o.get("message") or s)
                    journal[vid]["error"]=v["asr_error"]; save()
            except StopExternal: raise
            except Exception: still[vid]=(tid,v)
        pending=still; print(f"ASR完成 {len(done)}，处理中 {len(pending)}",flush=True)
    for vid, (tid, v) in pending.items():
        v["asr_error"]="转写等待超时"
        v["asr_task_id"]=tid
    return done

def clone_style(ws,src,dst):
    for c in range(1,37):
        a=ws.cell(src,c); b=ws.cell(dst,c); b._style=copy.copy(a._style); b.number_format=a.number_format; b.alignment=copy.copy(a.alignment)
    ws.row_dimensions[dst].height=ws.row_dimensions[src].height

def write_book(path,out,records,fetched,replace_sheets=None):
    wb=openpyxl.load_workbook(path)
    replace_sheets=replace_sheets or set()
    for rec in records:
        ws=wb[rec["sheet"]]; existing={str(ws.cell(r,5).value).split("/video/")[-1].split("?")[0]:r for r in range(3,ws.max_row+1) if "/video/" in str(ws.cell(r,5).value or "")}; blanks=[r for r in range(3,ws.max_row+1) if not ws.cell(r,5).value]; seq=max([ws.cell(r,1).value for r in range(3,ws.max_row+1) if isinstance(ws.cell(r,1).value,int)]+[0])
        if rec["sheet"] in replace_sheets:
            for row in ws.iter_rows(min_row=3,max_row=ws.max_row,min_col=1,max_col=19):
                for cell in row: cell.value=None
            existing={}; blanks=list(range(3,ws.max_row+1)); seq=0
        for v in rec["videos"]:
            row=existing.get(v["id"]); new=not row
            if not row:
                row=blanks.pop(0) if blanks else max(3,ws.max_row+1)
                if row>ws.max_row: clone_style(ws,max(3,row-1),row)
                seq+=1; ws.cell(row,1,seq); existing[v["id"]]=row
            for col,val in ((3,v["title"]),(4,v["bgm"]),(5,v["url"]),(6,v["publish"]),(7,fetched),(14,rec["followers"]),(15,v["likes"]),(16,v["comments"]),(17,v["collects"]),(18,v["shares"])): ws.cell(row,col,val)
            if new or not ws.cell(row,8).value:
                ws.cell(row,8,v.get("transcript","")); ws.cell(row,11,v.get("ending","")); ws.cell(row,12,v.get("hook",""))
            ws.cell(row,7).number_format="yyyy-mm-dd hh:mm:ss"; ws.cell(row,19,f'=IF(OR($N{row}="",$O{row}=""),"",ROUND($O{row}/$N{row},4))')
    wb.save(out)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--output"); ap.add_argument("--days",type=int,default=7); ap.add_argument("--only-sheets",default=""); ap.add_argument("--replace-sheets",default=""); a=ap.parse_args()
    cfg=json.loads((ROOT/"config.json").read_text()) if (ROOT/"config.json").exists() else {}; ov=json.loads((ROOT/"account_overrides.json").read_text()); get=lambda k:os.getenv(k.upper()) or cfg.get(k, "")
    missing=[k for k in ("tikhub_api_key","dasheng_uid","dasheng_api_key","dashscope_api_key") if not get(k)]
    if missing: ap.error("缺少配置项: "+", ".join(missing))
    src=Path(a.input).resolve(); out=Path(a.output).resolve() if a.output else src.parent/"outputs"/"douyin-weekly-workbook"/(src.stem+"_更新_"+datetime.now().strftime("%Y-%m-%d")+src.suffix); out.parent.mkdir(parents=True,exist_ok=True)
    rb=openpyxl.load_workbook(src,read_only=True,data_only=True); total=rb["相似博主总表"]
    if total.max_row is None: total.calculate_dimension(force=True)
    mapping={norm(total.cell(r,3).value):str(total.cell(r,4).value or "") for r in range(2,(total.max_row or 1)+1)}; tk=TikHub(get("tikhub_api_key")); since=int((datetime.now()-timedelta(days=a.days)).timestamp()); records=[]; failures=[]; unique={}
    only={x.strip() for x in a.only_sheets.split(",") if x.strip()}; replace={x.strip() for x in a.replace_sheets.split(",") if x.strip()}
    cached={}
    for sheet in rb.sheetnames[1:]:
        if sheet in replace: continue
        for row in rb[sheet].iter_rows(min_row=3, values_only=True):
            link=str(row[4] or "") if len(row)>4 else ""
            if "/video/" in link and len(row)>11 and row[7]:
                cached[link.split("/video/")[-1].split("?")[0]]=(row[7],row[11] or "",row[10] or "")
    for sheet in rb.sheetnames[1:]:
        if only and sheet not in only: continue
        ws=rb[sheet]; o=ov.get(sheet,{})
        try:
            if o.get("sec_uid"):
                try: sec,name,followers=tk.resolve_sec(o["sec_uid"])
                except StopExternal: raise
                except Exception: sec,name,followers=o["sec_uid"],sheet,None
            elif o.get("share_url"): sec,name,followers=tk.from_share(o["share_url"])
            else:
                ident=o.get("unique_id") or mapping.get(norm(sheet),"")
                if not ident: raise RuntimeError("无可靠账号映射")
                sec,name,followers=tk.resolve(ident)
            videos=tk.posts(sec,since)
            if not videos: videos=tk.posts(sec,0,pages=1)[:7]
            if followers is None: followers=next((v.get("_followers") for v in videos if v.get("_followers") is not None),None)
            for v in videos:
                try:
                    if v["id"] not in cached and v["id"] not in unique:
                        v["media"]=media(v["url"],get("dasheng_uid"),get("dasheng_api_key")); unique[v["id"]]=v
                except StopExternal: raise
                except Exception as e: v["media_error"]=str(e)
            records.append({"sheet":sheet,"name":name,"followers":followers,"videos":videos}); print(sheet,len(videos),flush=True)
        except StopExternal as e:
            failures.append({"sheet":sheet,"error":str(e),"stopped":True})
            selected=[x for x in rb.sheetnames[1:] if not only or x in only]
            index=selected.index(sheet)
            failures.extend({"sheet":x,"error":"外部调用停止，未处理"} for x in selected[index+1:])
            break
        except Exception as e: failures.append({"sheet":sheet,"error":str(e)}); print(sheet,"失败",e,flush=True)
    done=dict(cached)
    if not any(x.get("stopped") for x in failures):
        try: done.update(transcribe(list(unique.values()),get("dashscope_api_key")))
        except StopExternal as e: failures.append({"stage":"asr","error":str(e),"stopped":True})
    for r in records:
        for v in r["videos"]:
            if v["id"] in done: v["transcript"],v["hook"],v["ending"]=done[v["id"]]
    for r in records:
        for v in r["videos"]:
            for field in ("media_error", "asr_error"):
                if v.get(field): failures.append({"sheet":r["sheet"],"video_id":v["id"],"error":v[field]})
            if not v.get("transcript") and not v.get("media_error") and not v.get("asr_error"):
                failures.append({"sheet":r["sheet"],"video_id":v["id"],"error":"未取得逐字稿"})
    fetched=datetime.now().astimezone().replace(tzinfo=None); write_book(src,out,records,fetched,replace)
    report=out.with_suffix(".report.json"); report.write_text(json.dumps({"output":str(out),"accounts":len(records),"videos":sum(len(x["videos"]) for x in records),"failures":failures},ensure_ascii=False,indent=2))
    print(json.dumps({"output":str(out),"report":str(report),"failures":len(failures)},ensure_ascii=False))
if __name__=="__main__": main()
