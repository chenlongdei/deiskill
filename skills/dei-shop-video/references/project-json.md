# project.json 怎么写

一条视频的全部内容都在工程文件夹的 `project.json` 里；改完运行 `python3 scripts/finalize.py <工程> --snap-only` 看效果。完整例子：`templates/project.example.json`。

## 时间点写法

所有 `at`、`from`、`to`、`slam`、`strike_at` 字段都用同一套写法：

| 写法 | 意思 |
| --- | --- |
| `1.5` | 第 1.5 秒 |
| `"line:2"` / `"lineend:2"` | 第 2 句口播开始 / 说完 |
| `"word:9.9元就"` | 这几个字开始被说出的时刻（取第一次出现） |
| `"word:新店开业@2"` | 只在第 2 句里找 |
| `"end"` | 片尾 |
| 任意写法 + `"|-0.1"` / `"|+0.3"` | 提前 0.1 秒 / 延后 0.3 秒 |

`word:` 用的是口播原文里的字，找不到会报错。

## 字段

| 字段 | 说明 |
| --- | --- |
| `voice` | `voice_id`、`model`（eleven_v4）、`rate` 倍速、`gap` 句间停顿、`lead` 片头留白、`tail` 片尾留白、`volume` 人声音量 |
| `lines` | 口播，一句一项；改了要重跑 `tts.py make` |
| `captions` | 每句一组字幕分段，拼起来必须等于原句；`*字*` 标黄；`#` 开头的段不出底部字幕（有大花字时用） |
| `shots` | 镜头：`at` 从什么时候开始、`clip` 素材文件名、`from` 从素材第几秒开始用、`snap` 是否吸附节拍。看 `素材缩略图/` 挑画面 |
| `overlays` | 图层，见下表 |
| `sfx_dir`、`sfx` | 音效文件夹；每个音效 `name`（不带 .mp3）、`at`、`volume` |
| `bgm` | `file`、`offset`、`bpm`（bgm.py 自动写）、`volume`、`duck`、`source`（曲名作者许可） |
| `grade` | 调色，`adjust` 里 exposure / contrast / highlights / shadows / whites / blacks / temperature / tint / vibrance / saturation，范围 -1～1（exposure -2～2） |
| `fonts` | `caption`（字幕）、`display`（花字）、`number`（价格数字、定位钉、标签），文件放 `assets/fonts/` |
| `masks` | 要打马赛克的地方：`clip`、`w`、`h`、`keys`（`[素材秒数, 中心x, 中心y]`，素材原始像素），写好后运行 `mask.py` |
| `colors` | `brand` 品牌色（定位钉、卖点描边）、`accent`（服务标签） |

## 图层类型

| type | 字段 | 效果 |
| --- | --- | --- |
| `headline` | `big`、`small`、`from`、`to`、`slam`、`top` | 大标题（`big` 用数字字体）；`from` 对准口播说到它的字；`slam` 时再砸一次并震屏；`to` 时缩走 |
| `pin` | `text`、`top` | 定位钉 + 地址胶囊 |
| `speedlines` | `from`、`to` | 放射速度线 |
| `flash` | `from` | 闪白转场 |
| `ribbon` | `text`、`top` | 左侧滑入的红彩带 |
| `burst` | `text`、`prefix`、`top` | 低价爆炸贴 + 旋转光芒 + 金币飞散 |
| `tag` | `text`（可含 `<b>`）、`top` | 白底胶囊标签 |
| `pop` | `text`、`size`、`color`、`rot`、`top` | 卖点大字弹出 |
| `strike` | `text`（含 `<span class='old'>¥89<i class='strike'></i></span>`）、`strike_at` | 原价划线 |
| `impact` | `text`、`sub`、`size`、`color` | 冲屏大字 + 抖动 |
| `card` | `img` | 团购卡从下方弹出 |
| `arrow` | `left`、`top` | 指向左下角的跳动箭头 |

`pop`、`strike`、`impact` 可加 `font`：`disp`（花字，pop/strike 默认）、`num`（数字，impact 默认）、`cap`（字幕字体）。

`color` 可选：`yellow-red`、`yellow-black`、`white-brand`、`white-red`、`white-black`。

## 版面

画布 1080×1920。抖音界面会盖住上方约 280 像素、下方约 450 像素和右侧一条；文字放在 300–1250 之间。底部字幕在 1150。
