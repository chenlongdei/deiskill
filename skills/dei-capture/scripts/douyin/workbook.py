#!/usr/bin/env python3
"""监控工作簿：按「相似博主总表 + 每个博主一页」的 xlsx，抓各博主近 N 天作品，转写后增量写回新副本。

来自原 dei-daily-report 抖音模块，并入 dei-capture。只写客观数据：标题、BGM、链接、发布时间、抓取时间、
粉丝量、点赞、评论、收藏、转发、赞粉比、逐字稿、前 5 秒和结尾；不写分类、钩子类型等主观字段。

数据：Monid 或 TikHub（douyin.provider）；去水印：大圣（没配置时用 Monid）；转写：阿里云百炼 paraformer-v2。凭证都在 dei-capture 的 config.json。
用法（在 dei-capture 目录下）：
  python3 scripts/douyin/workbook.py init                      # 把模板复制到 <output_root>/抖音/监控工作簿/
  python3 scripts/douyin/workbook.py --input <工作簿.xlsx> [--days 7]   # 直接更新原表，先自动备份到 备份/；--output 另存
"""
from __future__ import annotations
import argparse, copy, json, os, re, shutil, sys, time
from datetime import datetime, timedelta
from pathlib import Path
import openpyxl
# Windows 中文系统默认 GBK：本脚本和它调用的 Python 工具（yt-dlp、notebooklm 等）一律用 UTF-8 输入输出
import os as _os, sys as _sys
_os.environ.setdefault("PYTHONUTF8", "1"); _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HttpError, data_provider, douyin_root, load_config, monid_run  # noqa: E402
from tikhub import TZ, StopExternal, TikHub, dasheng_media, find, norm, req  # noqa: E402

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
    journal=json.loads(ASR_JOURNAL.read_text(encoding="utf-8")) if ASR_JOURNAL.exists() else {}
    def save():
        ASR_JOURNAL.parent.mkdir(parents=True,exist_ok=True)
        temporary=ASR_JOURNAL.with_suffix(".tmp")
        temporary.write_text(json.dumps(journal,ensure_ascii=False,indent=2), encoding="utf-8")
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

SEC_RE = re.compile(r"/user/(MS4wLjAB[\w-]+)")
TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "抖音监控工作簿模板.xlsx"
TPL_SHEET = "_博主页模板"
TOTAL = "相似博主总表"


class MonidSource:
    """Monid 网关：作品列表带点赞、评论、收藏、转发；没有 BGM 和粉丝量（留空，不写 0）。"""

    def __init__(self, cfg):
        self.cfg = cfg

    def account(self, sec, name):
        return sec, name, None

    def posts(self, sec, since=0, pages=3):
        out, cursor = [], None
        for _ in range(pages):
            body = {"secUserId": sec, "limit": 20, "sort": "newest"}
            if cursor:
                body["cursor"] = cursor
            run = monid_run(self.cfg, "anyapi", "/douyin.user_posts", body)
            data = (run.get("output") or {}).get("data") or {}
            items = data.get("posts") or []
            for x in items:
                t = int(x.get("createdUtc") or 0)
                vid = str(x.get("id") or "")
                if not vid or t < since:
                    continue
                out.append({"id": vid, "title": str(x.get("caption") or ""), "url": f"https://www.douyin.com/video/{vid}",
                            "ts": t, "publish": datetime.fromtimestamp(t, TZ).strftime("%Y-%m-%d %H:%M:%S") if t else "",
                            "bgm": "", "likes": x.get("likes"), "comments": x.get("comments"),
                            "collects": x.get("saves"), "shares": x.get("shares"), "_followers": None})
            ts = [int(x.get("createdUtc") or 0) for x in items]
            cursor = data.get("nextCursor")
            if not items or not data.get("hasMore") or not cursor or (since and ts and min(ts) < since):
                break
        seen, uniq = set(), []
        for v in sorted(out, key=lambda x: x["ts"], reverse=True):
            if v["id"] not in seen:
                seen.add(v["id"]); uniq.append(v)
        return uniq


class TikHubSource:
    def __init__(self, token):
        self.tk = TikHub(token)

    def account(self, sec, name):
        try:
            return self.tk.resolve_sec(sec)
        except StopExternal:
            raise
        except Exception:
            return sec, name, None

    def posts(self, sec, since=0, pages=10):
        return self.tk.posts(sec, since, pages)


def safe_sheet_name(name):
    return re.sub(r"[\[\]\:\*\?\/\\]", " ", str(name)).strip()[:31] or "未命名"


def read_total(wb):
    """总表 → [(分页名, 抖音号, 主页 sec_uid)]；跳过示例行和空行。"""
    ws = wb[TOTAL]
    rows = []
    for r in range(2, (ws.max_row or 1) + 1):
        name = str(ws.cell(r, 3).value or "").strip()
        if not name or name.startswith("示例："):
            continue
        m = SEC_RE.search(str(ws.cell(r, 5).value or ""))
        rows.append((safe_sheet_name(name), str(ws.cell(r, 4).value or "").strip(), m.group(1) if m else ""))
    return rows


def prepare(src, out):
    """总表里有、但还没有分页的博主，从隐藏的模板页复制出分页。返回本次要读写的文件。"""
    wb = openpyxl.load_workbook(src)
    if TOTAL not in wb.sheetnames:
        raise SystemExit(f"工作簿里没有「{TOTAL}」页；用 workbook.py init 生成模板")
    created = []
    if TPL_SHEET in wb.sheetnames:
        for name, _, _ in read_total(wb):
            if name not in wb.sheetnames:
                ws = wb.copy_worksheet(wb[TPL_SHEET])
                ws.title, ws.sheet_state = name, "visible"
                ws.cell(1, 1, f"{name} · 对方视频（A:S 程序自动写入，人工列除外）")
                created.append(name)
    if not created:
        return src, []
    wb.save(out)
    return out, created


def blogger_sheets(wb):
    return [n for n in wb.sheetnames[1:] if not n.startswith("_") and wb[n].sheet_state == "visible"]


def backup_copy(src, keep=10):
    """直接更新前先备份到同目录「备份/」，只保留最近 keep 份。"""
    d = src.parent / "备份"
    d.mkdir(exist_ok=True)
    dst = d / f"{src.stem}_{datetime.now(TZ).strftime('%Y%m%d_%H%M%S')}{src.suffix}"
    shutil.copyfile(src, dst)
    olds = sorted(d.glob(f"{src.stem}_*{src.suffix}"))
    for f in olds[:-keep]:
        f.unlink()
    return dst


def cmd_init(args):
    target = Path(args.output).expanduser() if args.output else work_dir() / "抖音监控工作簿.xlsx"
    if target.exists():
        print(json.dumps({"command": "init", "file": str(target), "created": False, "note": "已存在，未覆盖"}, ensure_ascii=False))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE, target)
    print(json.dumps({"command": "init", "file": str(target), "created": True,
                      "next": "在「相似博主总表」填博主名称和主页链接，然后运行 workbook.py --input <这个文件>"}, ensure_ascii=False))


def main():
    global ASR_JOURNAL
    if sys.argv[1:2] == ["init"]:
        ip = argparse.ArgumentParser(prog="workbook.py init"); ip.add_argument("init"); ip.add_argument("--output")
        return cmd_init(ip.parse_args())
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--output"); ap.add_argument("--days",type=int,default=7); ap.add_argument("--only-sheets",default=""); ap.add_argument("--replace-sheets",default="")
    ap.add_argument("--overrides",help="账号覆盖表 JSON（默认 <output_root>/抖音/监控工作簿/account_overrides.json）"); a=ap.parse_args()
    wd=work_dir(); ASR_JOURNAL=wd/"asr_tasks.json"
    c=load_config(); provider=data_provider(c); ds=c.get("dasheng") or {}
    dash_key=os.getenv("DASHSCOPE_API_KEY") or (c.get("dashscope") or {}).get("api_key") or ""
    if not dash_key: ap.error("config.json 缺少 dashscope.api_key（阿里云百炼，转写用）")
    if provider=="tikhub": source=TikHubSource(c["tikhub_token"])
    elif provider=="monid": source=MonidSource(c)
    else: ap.error("没有可用的数据来源：配置 douyin.monid.token（Monid）或 tikhub.token（TikHub）")
    print(f"数据来源：{provider}；去水印：{'大圣' if ds.get('uid') and ds.get('key') else 'Monid'}",flush=True)
    def media_of(url):
        if ds.get("uid") and ds.get("key"): return media(url,ds["uid"],ds["key"])
        run=monid_run(c,"anyapi","/douyin.video",{"url":url}); m=((run.get("output") or {}).get("data") or {}).get("videoUrl")
        if not m: raise RuntimeError("Monid 无直链")
        return m
    ov_path=Path(a.overrides).expanduser() if a.overrides else wd/"account_overrides.json"
    ov=json.loads(ov_path.read_text(encoding="utf-8")) if ov_path.exists() else {}
    src0=Path(a.input).resolve()
    if not src0.exists(): ap.error(f"工作簿不存在：{src0}")
    if a.output:
        out=Path(a.output).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    else:
        out=src0; backup=backup_copy(src0); print(f"已备份：{backup}",flush=True)
    src,created=prepare(src0,out)
    if created: print("新建分页："+"、".join(created),flush=True)
    rb=openpyxl.load_workbook(src,read_only=False,data_only=True)
    total={name:(uid,sec) for name,uid,sec in read_total(rb)}
    sheets=blogger_sheets(rb)
    since=int((datetime.now()-timedelta(days=a.days)).timestamp()); records=[]; failures=[]; unique={}
    only={x.strip() for x in a.only_sheets.split(",") if x.strip()}; replace={x.strip() for x in a.replace_sheets.split(",") if x.strip()}
    cached={}
    for sheet in sheets:
        if sheet in replace: continue
        for row in rb[sheet].iter_rows(min_row=3, values_only=True):
            link=str(row[4] or "") if len(row)>4 else ""
            if "/video/" in link and len(row)>11 and row[7]:
                cached[link.split("/video/")[-1].split("?")[0]]=(row[7],row[11] or "",row[10] or "")
    for sheet in sheets:
        if only and sheet not in only: continue
        o=ov.get(sheet,{}); uid,home_sec=total.get(sheet,("",""))
        try:
            sec=o.get("sec_uid") or home_sec
            if sec: sec,name,followers=source.account(sec,sheet)
            elif provider=="tikhub" and o.get("share_url"): sec,name,followers=source.tk.from_share(o["share_url"])
            elif provider=="tikhub" and (o.get("unique_id") or uid): sec,name,followers=source.tk.resolve(o.get("unique_id") or uid)
            else: raise RuntimeError("缺少主页链接：在「相似博主总表」E 列填博主主页链接")
            videos=source.posts(sec,since)
            if not videos: videos=source.posts(sec,0,pages=1)[:7]
            if followers is None: followers=next((v.get("_followers") for v in videos if v.get("_followers") is not None),None)
            for v in videos:
                try:
                    if v["id"] not in cached and v["id"] not in unique:
                        v["media"]=media_of(v["url"]); unique[v["id"]]=v
                except StopExternal: raise
                except Exception as e: v["media_error"]=str(e)
            records.append({"sheet":sheet,"name":name,"followers":followers,"videos":videos}); print(sheet,len(videos),flush=True)
        except (StopExternal, HttpError) as e:
            if isinstance(e,HttpError) and not re.search(r"HTTP 40[123]|BLOCKED",str(e)):
                failures.append({"sheet":sheet,"error":str(e)}); print(sheet,"失败",e,flush=True); continue
            failures.append({"sheet":sheet,"error":str(e),"stopped":True})
            selected=[x for x in sheets if not only or x in only]
            index=selected.index(sheet)
            failures.extend({"sheet":x,"error":"外部调用停止，未处理"} for x in selected[index+1:])
            break
        except Exception as e: failures.append({"sheet":sheet,"error":str(e)}); print(sheet,"失败",e,flush=True)
    done=dict(cached)
    if not any(x.get("stopped") for x in failures):
        try: done.update(transcribe(list(unique.values()),dash_key))
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
    fetched=datetime.now(TZ).replace(tzinfo=None); write_book(src,out,records,fetched,replace)
    logs=out.parent/"运行记录"; logs.mkdir(exist_ok=True)
    report=logs/f"{out.stem}_{datetime.now(TZ).strftime('%Y%m%d_%H%M%S')}.report.json"; report.write_text(json.dumps({"output":str(out),"provider":provider,"created_sheets":created,"accounts":len(records),"videos":sum(len(x["videos"]) for x in records),"failures":failures},ensure_ascii=False,indent=2), encoding="utf-8")
    print(json.dumps({"output":str(out),"report":str(report),"provider":provider,"failures":len(failures)},ensure_ascii=False))
if __name__=="__main__": main()
