"""scenes_example.py —— 一条真实口播（3:00 → 2:05，「我离不开的 2 个 AI 工具」）的画面，v6c 定稿。
复制成工程里的 scenes.py，再按自己的口播改。这里写死的秒数是第一次剪（work/edl_base.json）的成片时间；
新写的视频优先用 W("口播里的字") 定位，改剪辑后自动跟着走。能用的函数见 references/scenes.md。
用到的 logo：openai（Codex）、obsidian、doubao、deepseek、word、markdown，放进 hf/assets/logos/。
"""

# =====================================================================
# 0–10  人像 · 钩子
cnt = put(0.55, f'<div class="stk"><div class="big" id="n100">0</div><div class="sm">个 AI 工具</div></div>', 170, 620, 'pop', 'pop')
counter(0.6, 'n100', 100)
S(0.6, 'riser', .6)
ok = put(3.0, pill(f'{ic("check-one", 40, INK)} 总有 1 个能帮你'), 215, 1010, 'slam', 'text_slam')
T(4.4, f'#{cnt} > .in', {'opacity': 0, 'x': -60}, .25, 'power2.in'); T(4.4, f'#{ok} > .in', {'opacity': 0, 'x': -60}, .25, 'power2.in')
sticker(7.9, 9.9, f'<div class="stk">{ic("list-checkbox", 96, NEON)}<div class="sm">日常 AI 清单</div></div>', 660)

# 10–21.1  IPO 模型
scene(10.0, 21.1, '01 · 底层模型', 'IPO 模型')
NX, NY = [210, 540, 870], 760
for k, (L, cn, icn, tt) in enumerate([('I', '输入', 'inbox', 16.75), ('P', '处理', 'cpu', 17.35), ('O', '输出', 'send', 18.15)]):
    i = put(11.0 + k * .35, node(f'<span class="L" id="L{k}">{L}</span><span class="ico" id="I{k}" style="opacity:0">{ic(icn, 90, NEON)}</span>', 210),
            NX[k], NY, 'pop', 'pop', .8)
    els[-1] = els[-1].replace('class="el ', f'class="el nd{k} ')
    put(tt, lab(cn, WHITE, 46), NX[k], NY + 165, 'up', 'tap', .7)
    T(tt, f'#L{k}', {'opacity': 0, 'scale': .5}, .2); A(tt, f'#I{k}', {'opacity': 0, 'scale': .5}, {'opacity': 1, 'scale': 1}, .3, 'back.out(2)')
for k in range(2):
    i = nid('ar'); els.append(f'<div class="arrow" id="{i}" style="left:{NX[k] + 112}px;top:{NY - 3}px;width:{NX[k + 1] - NX[k] - 224}px"></div>')
    A(12.2 + k * .3, f'#{i}', {'scaleX': 0}, {'scaleX': 1}, .4, 'power2.inOut')
# 「先看中间」：处理放大、发光，两边变暗
T(18.8, '.nd0 > .in', {'opacity': .25, 'scale': .85}, .35); T(18.8, '.nd2 > .in', {'opacity': .25, 'scale': .85}, .35)
T(18.8, '.nd1 > .in', {'scale': 1.28}, .45, 'back.out(1.6)'); S(18.8, 'sparkle', .7)
put(19.4, pill('今天只讲这一格', NEON, INK, 38), 540, 1010, 'up')
end_scene()

# 21.2–24.7 人像
sticker(21.3, 24.6, f'<div class="stk"><div class="big">2</div><div class="sm">个核心工具</div></div>', 640, kind='slam', sfx='text_slam')

# 24.7–32.3 两个工具
scene(24.7, 32.3, '02 · 处理', '两个核心工具')
put(25.4, f'<div class="tool">{logo("openai", 170)}<div class="tn">Codex</div></div>', 300, 760, 'pop', 'pop')
put(26.5, f'<div class="tool">{logo("obsidian", 170)}<div class="tn">Obsidian</div></div>', 780, 760, 'pop', 'pop')
put(26.0, '<div class="plus">+</div>', 540, 740, 'pop')
put(27.9, f'<div class="tag">{ic("robot-one", 40, INK)} AI Agent</div>', 300, 975, 'up', 'tap', .7)
put(28.6, '<div class="tag2">会动手干活</div>', 300, 1050, 'up')
put(29.8, f'<div class="tag">{ic("laptop", 40, INK)} 本地知识库</div>', 780, 975, 'up', 'tap', .7)
put(31.0, '<div class="tag2">笔记都在你电脑</div>', 780, 1050, 'up')
end_scene()

# 33.1–43.3 Codex vs 豆包 / DeepSeek：同一句话，两种结果；同一组卡片接着变成「聊天机器人 vs AI Agent」
scene(33.1, 43.3, '02 · 处理', '同一句话，两种结果')
put(33.3, '<div class="vcard" id="vr"></div>', 790, 900, 'pop', 'pop')
put(33.45, f'<div class="vhead">{logo("openai", 110)}<div class="vn">Codex</div></div>', 790, 790, 'up')
put(34.6, '<div class="vsb">VS</div>', 540, 900, 'slam', 'pop', .7, z=6)
put(35.64, '<div class="vcard" id="vl"></div>', 290, 900, 'pop', 'pop')
put(35.8, f'<div class="vhead"><div class="lrow">{logo("doubao", 96)}{logo("deepseek", 96)}</div><div class="vn">豆包 / DeepSeek</div></div>', 290, 790, 'up')
put(36.6, f'<div class="ask">{ic("comment", 40, INK)} 「帮我写一份周报」</div>', 540, 628, 'drop', 'pop', .7)
put(37.6, '<div class="res"><i></i><i></i><i class="s"></i><span>回你一段文字</span></div>', 290, 935, 'up', 'pop', .6)
put(38.9, f'<div class="res2">{logo("word", 84, .2)}<div><b>周报.docx</b><span>已存到桌面 ✓</span></div></div>', 790, 935, 'pop', 'ding')
put(40.13, '<div class="vl0">聊天机器人</div>', 290, 1055, 'up')
i = nid('x'); els.append(f'<div class="strike" id="{i}" style="left:80px;top:895px;width:420px;transform:rotate(-24deg);transform-origin:50% 50%"></div>')
A(41.0, f'#{i}', {'scaleX': 0}, {'scaleX': 1}, .25, 'power3.out'); S(41.0, 'strike')
T(41.1, '#vl', {'opacity': .45}, .3)
put(41.91, f'<div class="vl1">{ic("robot-one", 40, INK)} AI Agent · 能动手</div>', 790, 1055, 'pop', 'sparkle', .7)
T(41.91, '#vr', {'borderColor': NEON, 'boxShadow': '0 0 70px rgba(200,255,46,.35)'}, .35)
end_scene()

# 43.4–54.9 以前：4 步全手动
scene(43.4, 54.9, '03 · 对比', '以前：全靠手')
STEPS = [(45.98, 'magic', '让 AI 生成一段文本'), (47.8, 'file-word', '桌面新建 Word 文档'), (50.64, 'copy', '复制、粘贴进去'), (53.5, 'send', '再把文件发出去')]
for k, (t, icn, txt) in enumerate(STEPS):
    put(t, f'<div class="step"><span class="sn">{k + 1}</span>{ic(icn, 52, WHITE)}<span>{txt}</span></div>', 540, 660 + k * 125, 'left', 'tap')
els.append(f'<div class="ctr" id="ctr" style="opacity:0">手动 ×<b id="cn">1</b></div>')
A(45.98, '#ctr', {'opacity': 0, 'scale': .6}, {'opacity': 1, 'scale': 1}, .3, 'back.out(2)')
for k, (t, _, _) in enumerate(STEPS[1:], 2):
    settext(t - .01, 'cn', str(k - 1)); settext(t, 'cn', str(k))
    raw_js(f'tl.fromTo("#ctr",{{scale:1.3}},{{scale:1,duration:.3,ease:"back.out(2)",immediateRender:false}},{R(t):.2f});')
T(53.6, '#ctr', {'color': RED, 'borderColor': RED}, .3)
end_scene()

# 55.0–57.9 人像
sticker(55.0, 57.9, pill('现在 ↓', NEON, INK, 52), 640, kind='pop', sfx='pop')

# 57.9–66.8 现在：一句话
scene(57.9, 66.8, '03 · 对比', '现在：一句话')
BUB = '帮我生成这段文本，在桌面建个 Word'
els.append(f'<div class="bub" id="bub" style="opacity:0"><span id="btx"></span><i class="caret"></i></div>')
A(58.0, '#bub', {'opacity': 0, 'y': 30}, {'opacity': 1, 'y': 0}, .3)
typewrite(58.1, 'btx', BUB, 2.6)
S(58.1, 'typing', 1.0)   # 一段轻的键盘声，盖住整个打字动画（v6a 是三下重击，太冲）
gear = put(61.4, f'<div class="gear">{logo("openai", 140)}{ic("setting", 70, NEON)}</div>', 540, 770, 'pop', 'pop')
raw_js(f'tl.fromTo("#{gear} .gear .ic",{{rotation:0}},{{rotation:360,duration:1.6,ease:"none"}},{R(61.5):.2f});')
put(61.6, f'<div class="desk">{ic("computer", 44, GRAY)}<span>桌面</span></div>', 540, 935, 'up')
put(62.4, f'<div class="wfile">{logo("word", 92, .2)}<div class="okc">{ic("check-one", 38, INK)}</div></div>', 540, 935, 'drop', 'ding')
put(63.5, pill(f'{ic("tea-drink", 40, INK)} 你只需要等着', WHITE, INK, 38), 540, 1060, 'up', 'pop')
T(65.2, f'#bub', {'opacity': 0}, .2); T(65.2, f'#{gear} > .in', {'opacity': 0}, .2)
for _k in range(3): T(65.2, f'#{els[-1 - _k].split(chr(34))[1]} > .in', {'opacity': 0}, .2)
put(65.35, '<div class="big2"><s>4 步</s> → <b>1 句话</b></div>', 540, 820, 'slam', 'text_slam')
end_scene()

# 66.9–70.8 人像
sticker(67.0, 70.8, f'<div class="stk">{ic("cloud-storage", 96, WHITE)}<div class="sm">云端知识库</div></div>', 640)

# 70.8–78.5 云端两个问题
scene(70.8, 78.5, '04 · 知识库', '云端的两个坑')
put(71.0, node(ic('computer', 90, WHITE), 190), 230, 700, 'pop')
put(71.2, node(ic('cloudy', 90, WHITE), 190), 850, 700, 'pop')
i = nid('dl'); els.append(f'<div class="dash" id="{i}" style="left:335px;top:697px;width:410px"></div>'); A(71.3, f'#{i}', {'scaleX': 0}, {'scaleX': 1}, .4)
put(72.4, f'<div class="warn">{ic("eyes", 64, RED)}</div>', 540, 700, 'pop', 'impact', .6)
put(72.6, f'<div class="prob"><b>①</b> 隐私难保障</div>', 540, 880, 'left', None)
put(74.6, f'<div class="prob"><b>②</b> 接 AI 很麻烦 {ic("link-break", 46, RED)}</div>', 540, 990, 'left', 'impact', .6)
end_scene()

# 78.5–83.0 人像：Obsidian
sticker(78.6, 81.0, f'<div class="stk">{logo("obsidian", 120)}<div class="sm">Obsidian</div></div>', 640)
sticker(81.0, 83.0, pill(f'{ic("local", 40, INK)} 本地', NEON, INK, 46), 1010, 170, 'slam', 'text_slam')

# 83.0–88.4 笔记全在本机
scene(83.0, 88.4, '04 · 知识库', '笔记全在你电脑上')
put(83.2, f'<div class="lap">{ic("laptop", 260, WHITE, 2)}</div>', 540, 820, 'pop')
for k in range(6):
    x0, y0 = [150, 930, 120, 960, 260, 820][k], [560, 560, 900, 900, 1060, 1060][k]
    i = put(84.6 + k * .18, f'<div class="md">{logo("markdown", 64, .18)}<span>.md</span></div>', x0, y0, 'pop', 'pop' if k % 2 == 0 else None, .5)
    A(85.9 + k * .05, f'#{i}', {'x': 0, 'y': 0, 'scale': 1}, {'x': 540 - x0, 'y': 800 - y0, 'scale': .3}, .55, 'power2.in')
    T(86.4 + k * .05, f'#{i} > .in', {'opacity': 0}, .1)
put(86.6, f'<div class="shield">{ic("protect", 70, INK)}<span>存在本机</span></div>', 540, 1070, 'pop', 'ding')
end_scene()

# 88.5–93.4 人像
sticker(88.5, 93.4, f'<div class="stk vs">{logo("obsidian", 96)}{logo("openai", 96)}<div class="sm">组合起来</div></div>', 640)

# 93.4–110.6 两者配合：闭环
scene(93.4, 110.6, '05 · 配合', '笔记 ⇄ Codex 闭环')
put(93.7, f'<div class="tool">{logo("obsidian", 150)}<div class="tn">笔记库</div></div>', 230, 700, 'pop', 'pop')
put(94.2, f'<div class="tool">{logo("openai", 150)}<div class="tn">Codex</div></div>', 850, 700, 'pop', 'pop')
i = nid('ln'); els.append(f'<div class="dash" id="{i}" style="left:330px;top:640px;width:420px"></div>'); A(95.3, f'#{i}', {'scaleX': 0}, {'scaleX': 1}, .4)
i2 = nid('ln'); els.append(f'<div class="dash g" id="{i2}" style="left:330px;top:760px;width:420px"></div>'); A(102.1, f'#{i2}', {'scaleX': 0}, {'scaleX': 1}, .4)
put(95.6, '<div class="lt">输入 →</div>', 540, 600, 'up', 'tap', .6)
for k in range(3):   # 文件从笔记库飞向 Codex
    i = nid('f'); els.append(f'<div class="fly" id="{i}" style="left:330px;top:620px">{ic("file-text", 40, WHITE)}</div>')
    raw_js(f'tl.fromTo("#{i}",{{x:0,opacity:0}},{{x:390,opacity:1,duration:1.1,ease:"power1.inOut"}},{R(96.2 + k * .5):.2f});tl.to("#{i}",{{opacity:0,duration:.15}},{R(97.3 + k * .5):.2f});')
put(100.9, pill(f'{ic("setting", 40, INK)} 处理', NEON, INK, 38), 850, 870, 'pop', 'pop')
put(102.4, '<div class="lt g">← 结果回来</div>', 540, 805, 'up', 'tap', .6)
for k in range(3):
    i = nid('f'); els.append(f'<div class="fly" id="{i}" style="left:720px;top:740px">{ic("file-text", 40, NEON)}</div>')
    raw_js(f'tl.fromTo("#{i}",{{x:0,opacity:0}},{{x:-390,opacity:1,duration:1.1,ease:"power1.inOut"}},{R(102.6 + k * .5):.2f});tl.to("#{i}",{{opacity:0,duration:.15}},{R(103.7 + k * .5):.2f});')
put(105.1, f'<div class="tag">{ic("puzzle", 40, INK)} 插件</div>', 230, 880, 'up', 'tap', .6)
# 关系图谱：节点和连线逐个长出来
G = [(540, 1010, 16), (430, 960, 10), (650, 950, 11), (380, 1060, 8), (700, 1060, 9), (540, 900, 9), (300, 990, 7), (780, 990, 7), (470, 1110, 7), (620, 1110, 8)]
E = [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 6), (2, 7), (3, 8), (4, 9), (1, 5), (2, 5), (8, 9)]
svg = ''.join(f'<line id="ge{k}" x1="{G[a][0]}" y1="{G[a][1]}" x2="{G[b][0]}" y2="{G[b][1]}" stroke="{NEON}" stroke-opacity=".55" stroke-width="3" stroke-dasharray="300" stroke-dashoffset="300"/>' for k, (a, b) in enumerate(E))
svg += ''.join(f'<circle id="gn{k}" cx="{x}" cy="{y}" r="{r}" fill="{NEON if k == 0 else WHITE}" opacity="0"/>' for k, (x, y, r) in enumerate(G))
els.append(f'<svg class="graph" width="1080" height="1920" viewBox="0 0 1080 1920">{svg}</svg>')
for k in range(len(G)): A(106.8 + k * .09, f'#gn{k}', {'opacity': 0, 'scale': 0, 'transformOrigin': '50% 50%'}, {'opacity': 1, 'scale': 1}, .3, 'back.out(2)')
for k in range(len(E)): T(107.0 + k * .07, f'#ge{k}', {'strokeDashoffset': 0}, .4, 'power2.out')
S(106.8, 'sparkle', .8)
put(107.0, '<div class="lt g">关系图谱</div>', 540, 1180, 'up')
end_scene()

# 110.6–113.8 人像
sticker(110.7, 113.6, pill('1 + 1 ＞ 2', NEON, INK, 52), 1010, 200, 'slam', 'text_slam')

# 113.6–124 结尾：下期 + 关注
scene(113.6, 124.3, '下期预告', '输入和输出，下期讲')
for k, (cn, icn) in enumerate([('输入', 'inbox'), ('处理', 'cpu'), ('输出', 'send')]):
    on = k == 1
    put(113.9 + k * .15, node(ic(icn, 80, INK if on else NEON), 180, NEON if on else TILE, NEON if not on else NEON), NX[k], 740, 'pop', 'pop', .6)
    put(114.1 + k * .15, lab(cn, WHITE, 42), NX[k], 880, 'up')
    if not on: put(115.0 + k * .1, '<div class="soon">下期</div>', NX[k], 640, 'pop', 'tap', .6)
    else: put(114.6, f'<div class="okc big">{ic("check-one", 44, INK)}</div>', NX[k] + 70, 670, 'pop', 'ding')
els.append(f'<div class="el" style="left:540px;top:1060px"><div class="in" id="fol" style="opacity:0"><div id="follow"><span id="f1">＋ 关注</span><span id="f2" style="opacity:0">✓ 已关注</span></div></div></div>')
A(117.2, '#fol', {'opacity': 0, 'scale': .6}, {'opacity': 1, 'scale': 1}, .35, 'back.out(2)')
els.append('<div id="touch"></div>')
A(118.3, '#touch', {'opacity': 0, 'scale': 1.6}, {'opacity': 1, 'scale': 1}, .25); T(118.75, '#touch', {'opacity': 0, 'scale': 1.4}, .25)
T(118.55, '#f1', {'opacity': 0}, .12); T(118.55, '#f2', {'opacity': 1}, .12); T(118.55, '#follow', {'backgroundColor': WHITE}, .15)
S(118.5, 'tap'); S(118.6, 'ding', .8)
end_scene()

