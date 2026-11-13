#!/usr/bin/env python3
"""课程物料包打包脚本（双 zip：Win 版 GBK + Mac 版 UTF-8，解压直出完整文件夹结构）

用法:
  python3 pack_materials.py <物料目录> <zip输出前缀> --root <根文件夹名> --structure <结构JSON文件>
  （或改 CONFIG 后按上述参数运行）

产物:
  <前缀>-Win版.zip   文件名 GBK 字节 + flag=0（手工构造 zip 结构），
                     Windows 资源管理器自带解压中文不乱码，微信直发
  <前缀>-Mac版.zip   文件名 UTF-8（Python zipfile 默认），Mac/Linux 正常

原理说明（重要，勿改回 zipfile 写 Win 版）:
  Python zipfile 对非 ASCII 文件名会强制置 UTF-8 flag（0x800），手动清零无效，
  且 encode('gbk').decode('cp437') 的中间层会污染字节（cp437 roundtrip 不保证无损）。
  因此 Win 版必须完全手工构造 zip 二进制：LFH/CDH/EOCD 逐字段 struct.pack，
  文件名直接写 GBK 字节、flag=0。Windows 对 flag=0 的名字按系统 ANSI(GBK) 解码，恰好还原。
"""
import sys
import json
import struct
import zlib
import zipfile
import tempfile
import shutil
import os

# ============ CONFIG（按课程主题修改这里） ============
DEFAULT_ROOT = '我的AI表格'
DEFAULT_STRUCTURE = {
    '01-乱数据': [],    # 填课堂物料文件名
    '02-干净表格': [],
    '03-分析报告': [],
    '04-课后练习': [],  # 课后练习数据（必有，作业配套）
}
README = '使用说明.txt'   # 物料目录里的说明文件名（txt 通用性最好）
# =====================================================

# zip 结构体格式（字段数已逐字节验证，勿改）
LFH_FMT = '<4sHHHHHIIIHH'           # 11 项 30 字节
CDH_FMT = '<4sHHHHHHIIIHHHHHII'     # 17 项 46 字节（含 comment_len）
EOCD_FMT = '<4sHHHHIIH'             # 8 项 22 字节


def make_gbk_zip(src_files, zip_path):
    """Win 版：手工构造 zip，文件名 GBK 字节 + flag=0。
    src_files: [(arcname, fpath 或 None=目录), ...] 按顺序写入。"""
    out = open(zip_path, 'wb')
    central = []
    for arcname, fpath in src_files:
        name_bytes = arcname.encode('gbk')
        if fpath is None:
            crc = 0; comp = b''; usize = 0; eattr = (0o40755 << 16) | 0x10; method = 0  # 目录=stored
        else:
            raw = open(fpath, 'rb').read()
            co = zlib.compressobj(6, zlib.DEFLATED, -15)   # raw deflate（zlib.compress 带 header，zip 不认）
            comp = co.compress(raw) + co.flush()
            crc = zlib.crc32(raw) & 0xFFFFFFFF
            usize = len(raw); eattr = 0o100644 << 16; method = 8                   # 文件=deflate
        lfh_off = out.tell()
        out.write(struct.pack(LFH_FMT, b'PK\x03\x04', 20, 0, method, 0, 0x5441,
                              crc, len(comp), usize, len(name_bytes), 0))
        out.write(name_bytes)
        out.write(comp)
        central.append((lfh_off, name_bytes, crc, len(comp), usize, eattr, method))
    cd_off = out.tell()
    for lfh_off, name_bytes, crc, csize, usize, eattr, method in central:
        out.write(struct.pack(CDH_FMT, b'PK\x01\x02', 20, 20, 0, method, 0, 0x5441,
                              crc, csize, usize, len(name_bytes), 0, 0, 0, 0, eattr, lfh_off))
        out.write(name_bytes)   # CDH 后必须跟名字（曾漏写，勿删）
    cd_size = out.tell() - cd_off
    n = len(central)
    out.write(struct.pack(EOCD_FMT, b'PK\x05\x06', 0, 0, n, n, cd_size, cd_off, 0))
    out.close()


def make_utf8_zip(src_files, zip_path):
    """Mac 版：zipfile 常规写法（自动置 UTF-8 flag）。"""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for arcname, fpath in src_files:
            if fpath is None:
                z.mkdir(arcname)
            else:
                z.write(fpath, arcname)


def build_items(src_dir, root, structure):
    items = [(f'{root}/', None), (f'{root}/{README}', os.path.join(src_dir, README))]
    for sub, files in structure.items():
        items.append((f'{root}/{sub}/', None))
        for f in files:
            items.append((f'{root}/{sub}/{f}', os.path.join(src_dir, f)))
    return items


def verify_gbk(zip_path, root, structure):
    """Win 版验证：flag=0、GBK 名可还原、CRC 全过、目录树齐全。"""
    ok = True
    z = zipfile.ZipFile(zip_path)
    for info in z.infolist():
        if info.flag_bits & 0x800:
            print(f'  ❌ Win版不应置 UTF-8 flag: {info.filename}')
            ok = False
        try:
            info.filename.encode('cp437').decode('gbk')
        except Exception as e:
            print(f'  ❌ GBK 还原失败: {info.filename} {e}')
            ok = False
    disp = [n.encode('cp437').decode('gbk') for n in z.namelist()]
    expect = {f'{root}/', f'{root}/{README}'}
    expect |= {f'{root}/{sub}/' for sub in structure}
    expect |= {f'{root}/{sub}/{f}' for sub, files in structure.items() for f in files}
    if expect - set(disp):
        print(f'  ❌ Win版缺条目: {expect - set(disp)}')
        ok = False
    if z.testzip() is not None:
        print('  ❌ Win版 CRC 校验失败')
        ok = False
    return ok


def verify_utf8(zip_path, root, structure):
    """Mac 版验证：UTF-8 flag 置位、目录树齐全、解压实测。"""
    ok = True
    z = zipfile.ZipFile(zip_path)
    for info in z.infolist():
        if not (info.flag_bits & 0x800):
            print(f'  ❌ Mac版未置 UTF-8 flag: {info.filename}')
            ok = False
    expect = {f'{root}/', f'{root}/{README}'}
    expect |= {f'{root}/{sub}/' for sub in structure}
    expect |= {f'{root}/{sub}/{f}' for sub, files in structure.items() for f in files}
    if expect - set(z.namelist()):
        print(f'  ❌ Mac版缺条目: {expect - set(z.namelist())}')
        ok = False
    d = tempfile.mkdtemp()
    try:
        z.extractall(d)
        if not os.path.isdir(os.path.join(d, root)):
            print('  ❌ Mac版解压后无根文件夹')
            ok = False
    finally:
        shutil.rmtree(d)
    return ok


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src_dir, prefix = sys.argv[1], sys.argv[2]
    root, structure = DEFAULT_ROOT, DEFAULT_STRUCTURE
    if '--root' in sys.argv:
        root = sys.argv[sys.argv.index('--root') + 1]
    if '--structure' in sys.argv:
        structure = json.load(open(sys.argv[sys.argv.index('--structure') + 1], encoding='utf-8'))

    items = build_items(src_dir, root, structure)
    win_zip, mac_zip = f'{prefix}-Win版.zip', f'{prefix}-Mac版.zip'
    make_gbk_zip(items, win_zip)
    make_utf8_zip(items, mac_zip)
    print(f'Win: {os.path.getsize(win_zip)} bytes | Mac: {os.path.getsize(mac_zip)} bytes')
    ok_w = verify_gbk(win_zip, root, structure)
    ok_m = verify_utf8(mac_zip, root, structure)
    print('✅ 双包校验通过' if (ok_w and ok_m) else '⚠️ 校验未通过')


if __name__ == '__main__':
    main()
