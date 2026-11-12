#!/usr/bin/env python3
"""监控工作簿：按「相似博主总表 + 每个博主一页」的 xlsx，抓各博主近 N 天作品，转写后增量写回新副本。

来自原 dei-daily-report 抖音模块，并入 dei-capture。只写客观数据：标题、BGM、链接、发布时间、抓取时间、
粉丝量、点赞、评论、收藏、转发、赞粉比、逐字稿、前 5 秒和结尾；不写分类、钩子类型等主观字段。

数据：TikHub；去水印：大圣；转写：阿里云百炼 paraformer-v2。凭证都在 dei-capture 的 config.json。
用法（在 dei-capture 目录下）：python3 scripts/douyin/workbook.py --input <工作簿.xlsx> [--days 7]
"""
from __future__ import annotations
import argparse, copy, json, os, sys, time
from datetime import datetime, timedelta
from pathlib import Path
import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import douyin_root, load_config  # noqa: E402
from tikhub import StopExternal, TikHub, dasheng_media, find, norm, req  # noqa: E402

DS = "https://dashscope.aliyuncs.com/api/v1"


def work_dir():
    root = douyin_root()
    if root is None:
        raise SystemExit("未配置采集结果保存位置：先按 dei-capture 的 SKILL.md「首次配置」写入 output_root")
    return root / "监控工作簿"


ASR_JOURNAL = None  # main() 里设为 <output_root>/抖音/监控工作簿/asr_tasks.json


def media(url, uid, key):
    return dasheng_media(url, uid, key)[0]


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
    global ASR_JOURNAL
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--output"); ap.add_argument("--days",type=int,default=7); ap.add_argument("--only-sheets",default=""); ap.add_argument("--replace-sheets",default="")
    ap.add_argument("--overrides",help="账号覆盖表 JSON（默认 <output_root>/抖音/监控工作簿/account_overrides.json）"); a=ap.parse_args()
    wd=work_dir(); ASR_JOURNAL=wd/"asr_tasks.json"
    c=load_config()
    vals={"tikhub_api_key":c.get("tikhub_token"),"dasheng_uid":(c.get("dasheng") or {}).get("uid"),"dasheng_api_key":(c.get("dasheng") or {}).get("key"),"dashscope_api_key":(c.get("dashscope") or {}).get("api_key")}
    get=lambda k:os.getenv(k.upper()) or vals.get(k) or ""
    names={"tikhub_api_key":"tikhub.token","dasheng_uid":"douyin.dasheng.uid","dasheng_api_key":"douyin.dasheng.key","dashscope_api_key":"dashscope.api_key"}
    missing=[names[k] for k in names if not get(k)]
    if missing: ap.error("config.json 缺少: "+", ".join(missing))
    ov_path=Path(a.overrides).expanduser() if a.overrides else wd/"account_overrides.json"
    ov=json.loads(ov_path.read_text(encoding="utf-8")) if ov_path.exists() else {}
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
