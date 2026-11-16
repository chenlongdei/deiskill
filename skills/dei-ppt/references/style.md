# 版式与配图规范

## 画布与颜色

- 16:9，13.333 × 7.5 英寸；白底。
- 颜色：黑 1A1A1A、灰 8A8A8A、浅灰 C8C8C8、红 E60012（唯一强调色）、蓝 1F5BD6（只用于左右对比）。
- 字体：思源黑体（Source Han Sans SC），东亚字体通过 XML 的 `a:ea` / `a:cs` 指定。正文 ≥ 22 号，页眉小字 15 号，来源 13 号。
- 左右边距 0.9 英寸。页眉小字放在 y=0.3（`EB()` 标出当前模块），标题放在 y=0.65—0.9，38 号加粗。

## 文字标记（写在字符串里）

`{红色}`　`[蓝色]`　`~删除线~`。一行一个段落，方便讲者逐行加动画。

## 元素与页面模板（`scripts/deck_engine.py`）

| 函数 | 用途 |
|---|---|
| `T(x,y,w,h,lines,size,bold,align,color,anchor,ls)` | 文字框 |
| `IMG(path,x,y,w,h,border)` | 图片，等比缩放后居中放进框里 |
| `R(...)` / `PH(x,y,w,h,label)` | 色块 / 截图占位框 |
| `statement(lines, sub)` | 整页一句话 |
| `titled(title, lines, img)` | 标题 + 要点（+ 右侧配图） |
| `progress(k, sections, subs)` | 路线图（k=-1 全亮） |
| `hero(img, title, sub, eyebrow)` | 主视觉页：图满版铺底，左侧放可编辑文字 |
| `summary(img, eyebrow, title, points, foot)` | 小结拍照页：一句话 + 三条要点 |
| `bubble()` / `code()` | 对话气泡 / 指令块 |
| `EB(text)` | 页眉：当前模块 |
| `S(say, els, sec)` | 加一页（讲稿, 元素, 段落） |
| `build(base, filename)` | 输出 PPTX + preview + 逐页讲稿 |

## 生图风格串（直接复制进 spec JSON 的 `style`）

**主视觉（封面、模块封面、小结、封底）**：纸艺立体风格，左侧 45% 留白，用 2k、high 质量：

```
Premium editorial key visual for a keynote slide, 16:9. Soft matte 3D paper-craft style: objects look made of thick white and warm off-white paper with crisp folded edges, gentle soft daylight from the upper left, delicate soft shadows, shallow depth. Palette: white, warm greys, light wood, with Chinese red #E60012 as the ONLY accent color used sparingly. Calm, hopeful, dignified, clean, photographed-like realism of a paper diorama. COMPOSITION RULE: the LEFT 45% of the frame is pure empty white (#FFFFFF) background with nothing in it, reserved for a title; all subjects sit in the RIGHT 55%, and the background blends seamlessly into pure white toward the left edge and the top. Absolutely no text, no letters, no numbers, no Chinese characters, no logos, no watermark, no screens with UI, no realistic human faces (people, if any, are small faceless paper figures).
```

主视觉要有叙事：封面和封底用同一个场景，状态前后对照（例：封面是一摞稿子化成纸鹤飞走，封底桌面只剩一份成品，纸鹤落到青年身边）。主视觉页的标题如果压到画面，就把字号调小（模块封面 46—60 号）。

**页内小插图**：线稿，用 1:1、medium 质量：

```
Minimal flat vector spot illustration for a presentation slide, on a pure white background (#FFFFFF). Clean thin black line art (uniform stroke), very light grey fills only where needed, and exactly ONE small accent in Chinese red #E60012. Calm, friendly, professional, generous whitespace around the object, centered. Absolutely no text, no letters, no numbers, no Chinese characters, no logos, no watermark, no people's faces, no shadows, no gradients, no 3D.
```

小插图生成后，裁到内容边界并留 3% 边距，接近白色的像素洗成纯白。

## 截图

- 网页截图：`Chrome --headless=new --window-size=1400,2000 --virtual-time-budget=8000 --screenshot`，然后裁出关键区域，加 1pt 灰色边框，页脚注明来源。
- docx / xlsx 缩略图：`qlmanage -t -s 1600 <文件>`。
- 软件操作截图由讲者实测后补；可以叠加红框、红箭头。
