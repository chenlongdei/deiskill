#!/usr/bin/env python3
"""生成「抖音监控工作簿」模板：templates/抖音监控工作簿模板.xlsx。

结构：
- 相似博主总表：用户只填这一页（博主名称 + 主页链接，抖音号可选）
- _博主页模板（隐藏）：workbook.py 遇到总表里还没有分页的博主时，复制它新建分页
- 每个博主一页：第 1 行标题，第 2 行表头，第 3 行起是数据。A:S 由程序写入（对方视频的客观数据），
  T:AJ 是用户自己的创作与复盘区，程序永远不碰

用法：python3 scripts/douyin/make_template.py [--output 路径]
"""

import argparse
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

SKILL = Path(__file__).resolve().parents[2]
DEFAULT_OUT = SKILL / "templates" / "抖音监控工作簿模板.xlsx"

# A:S 程序写入；（人工）列程序不写
VIDEO_COLS = [
    ("序号", 6), ("分类（人工）", 10), ("标题", 36), ("BGM", 16), ("视频链接", 28), ("发布时间", 18),
    ("抓取时间", 18), ("视频文案（逐字稿）", 48), ("内容逻辑（人工）", 20), ("核心论点（人工）", 20),
    ("结尾", 28), ("前5秒钩子", 28), ("钩子类型（人工）", 12), ("粉丝量", 11), ("点赞", 9), ("评论", 9),
    ("收藏", 9), ("转发", 9), ("赞粉比", 9),
]
MINE_COLS = [
    ("值得借鉴吗", 10), ("借鉴点", 24), ("我的选题", 22), ("我的标题", 24), ("我的开头", 24), ("我的文案/链接", 28),
    ("发布日期", 12), ("播放", 9), ("点赞", 9), ("评论", 9), ("收藏", 9), ("转发", 9), ("涨粉", 9),
    ("做对了什么", 24), ("要改什么", 24), ("下一步", 20), ("备注", 20),
]
TOTAL_COLS = [("序号", 6), ("分组（可选）", 12), ("博主名称", 18), ("抖音号（可选）", 16),
              ("主页链接（必填，浏览器打开博主主页复制地址栏）", 56), ("备注", 30)]

THIN = Side(style="thin", color="D0D5DD")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_THEM = PatternFill("solid", fgColor="1F4E79")
HEAD_MINE = PatternFill("solid", fgColor="7A4E00")
HEAD_TOTAL = PatternFill("solid", fgColor="2F5D50")
MINE_BODY = PatternFill("solid", fgColor="FFF8E6")
WHITE = Font(bold=True, color="FFFFFF")
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)


def head(ws, row, cols, start, fill):
    for i, (name, width) in enumerate(cols):
        c = ws.cell(row, start + i, name)
        c.fill, c.font, c.alignment, c.border = fill, WHITE, CENTER, BORDER
        ws.column_dimensions[get_column_letter(start + i)].width = width


def body_row(ws, row):
    """一行空数据格式；workbook.py 追加新行时复制这一行的样式。"""
    for col in range(1, len(VIDEO_COLS) + len(MINE_COLS) + 1):
        c = ws.cell(row, col)
        c.border, c.alignment = BORDER, WRAP
        if col > len(VIDEO_COLS):
            c.fill = MINE_BODY
    ws.cell(row, 6).number_format = "yyyy-mm-dd hh:mm"
    ws.cell(row, 7).number_format = "yyyy-mm-dd hh:mm:ss"
    for col in range(14, 19):
        ws.cell(row, col).number_format = "#,##0"
    ws.cell(row, 19).number_format = "0.00%"
    ws.row_dimensions[row].height = 60


def build(out: Path) -> Path:
    wb = Workbook()
    total = wb.active
    total.title = "相似博主总表"
    head(total, 1, TOTAL_COLS, 1, HEAD_TOTAL)
    total.freeze_panes = "A2"
    total.row_dimensions[1].height = 36
    for r in range(2, 32):
        for col in range(1, len(TOTAL_COLS) + 1):
            total.cell(r, col).border = BORDER
        total.cell(r, 1, r - 1)
    total.cell(2, 3, "示例：把这一行换成你的对标博主")
    total.cell(2, 5, "https://www.douyin.com/user/MS4wLjABAAAA...")
    total.cell(2, 6, "博主名称会成为分页名；改名后在分页和这里同步改")

    tpl = wb.create_sheet("_博主页模板")
    tpl.cell(1, 1, "对方视频（A:S 程序自动写入，人工列除外）")
    tpl.cell(1, len(VIDEO_COLS) + 1, "我的创作与复盘（T:AJ 自己填写，程序不会改动）")
    tpl.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(VIDEO_COLS))
    tpl.merge_cells(start_row=1, start_column=len(VIDEO_COLS) + 1, end_row=1,
                    end_column=len(VIDEO_COLS) + len(MINE_COLS))
    for col, fill in ((1, HEAD_THEM), (len(VIDEO_COLS) + 1, HEAD_MINE)):
        c = tpl.cell(1, col)
        c.fill, c.font, c.alignment = fill, WHITE, CENTER
    head(tpl, 2, VIDEO_COLS, 1, HEAD_THEM)
    head(tpl, 2, MINE_COLS, len(VIDEO_COLS) + 1, HEAD_MINE)
    tpl.row_dimensions[1].height = 24
    tpl.row_dimensions[2].height = 32
    for r in range(3, 13):
        body_row(tpl, r)
    tpl.freeze_panes = "D3"
    dv = DataValidation(type="list", formula1='"是,否,待定"', allow_blank=True)
    tpl.add_data_validation(dv)
    dv.add(f"T3:T500")
    tpl.sheet_state = "hidden"

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(DEFAULT_OUT))
    print(build(Path(ap.parse_args().output)))
