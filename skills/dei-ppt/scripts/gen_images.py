#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 APIMart 的 GPT-Image-2.6 按幻灯片清单逐页生图。
用法：python3 gen_images.py <slides.json> <输出目录> [--only id1,id2] [--quality medium] [--model gpt-image-2.6-flare]
key 读取顺序：环境变量 APIMART_API_KEY → ~/.config/apimart/key
slides.json：[{"id": "s01", "prompt": "..."}, ...]，全局风格前缀放在 {"style": "..."} 里。"""
import json, os, sys, time, urllib.request, urllib.error, concurrent.futures as cf

API = 'https://api.apimart.ai/v1'
KEY = os.environ.get('APIMART_API_KEY') or open(os.path.expanduser('~/.config/apimart/key')).read().strip()

def req(method, path, body=None):
    r = urllib.request.Request(API + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=60) as f:
        return json.load(f)

def gen_one(slide, style, out, model, quality):
    path = os.path.join(out, f"{slide['id']}.png")
    if os.path.exists(path) and '--force' not in sys.argv:
        return slide['id'], 'skip(已存在)'
    body = {'model': model, 'prompt': style + '\n\n' + slide['prompt'], 'size': slide.get('size', spec_size),
            'resolution': slide.get('resolution', spec_res), 'quality': quality, 'n': 1, 'output_format': 'png'}
    try:
        tid = req('POST', '/images/generations', body)['data'][0]['task_id']
    except urllib.error.HTTPError as e:
        return slide['id'], f'提交失败 {e.code} {e.read()[:300]}'
    for _ in range(120):
        time.sleep(4)
        d = req('GET', f'/tasks/{tid}?language=zh')['data']
        st = d.get('status')
        if st == 'completed':
            url = d['result']['images'][0]['url']
            url = url[0] if isinstance(url, list) else url
            urllib.request.urlretrieve(url, path)
            json.dump(d.get('usage', {}), open(path[:-4] + '.usage.json', 'w'))
            return slide['id'], f"ok usage={d.get('usage')}"
        if st == 'failed':
            return slide['id'], f"失败 {d.get('error')}"
    return slide['id'], f'超时 task={tid}'

def main():
    global spec_size, spec_res
    spec = json.load(open(sys.argv[1], encoding='utf-8'))
    spec_size, spec_res = spec.get('size', '16:9'), spec.get('resolution', '2k')
    out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    only = set(arg('--only', '').split(',')) - {''}
    model, quality = arg('--model', 'gpt-image-2.6-flare'), arg('--quality', 'medium')
    slides = [s for s in spec['slides'] if s.get('engine', 'image') == 'image' and (not only or s['id'] in only)]
    print(f'生成 {len(slides)} 张，模型 {model}，质量 {quality}')
    with cf.ThreadPoolExecutor(4) as ex:
        for sid, msg in ex.map(lambda s: gen_one(s, spec['style'], out, model, quality), slides):
            print(sid, msg, flush=True)

if __name__ == '__main__':
    main()
