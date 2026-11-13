# 发布到 Notion：推送流程与排版规范

> 发布平台是 Notion 时加载。通用规则（发布记录、确认点、不开公开分享）见 `publish.md`，先读它。
> 排版规范基于 Notion-flavored Markdown Spec（`notion://docs/notion-flavored-markdown-spec`，可用 fetch 工具读取该 URI 获取最新版）与实际项目验证。

## 〇、推送流程（按序执行）

### 第 0 步：读规范

通读本文件（空行规则、块映射、防死链、附件、更新策略、验证清单），再动 Notion。

### 第 1 步：准备

1. 选通道（二选一，优先已经能用的那个）：
   - **Notion 连接器**：当前 Agent 已接好 Notion（工具名里带 notion 的 fetch / update-page / create-file-upload），先加载它们的参数说明。
   - **官方命令行 `ntn`**（2026-11-13 实测 0.23.30）：`ntn whoami` 显示工作空间即为已登录。没登录时运行 `ntn login`，把它打印的链接和验证码给用户，用户在浏览器确认后运行 `ntn login poll` 等它完成。常用命令（参数以 `ntn <命令> --help` 为准）：

     ```bash
     ntn pages get <page_id>                                  # 读页面，返回 Markdown（含属性）
     ntn pages create --parent page:<id> --json < 手册.md      # 新建；父级也可以是 database:<id> / data-source:<id>
     ntn pages edit <page_id> --json < 手册.md                 # 整页替换正文（相当于全量替换）
     ID=$(ntn files create --plain --filename "<名>.zip" < <名>.zip | cut -f1)   # 上传附件，1 小时内要挂到页面上
     ntn files get "$ID"                                      # 状态是 uploaded 再挂
     ntn api "v1/blocks/<page_id>/children" -X PATCH 'children[0][type]=file' \
       'children[0][file][type]=file_upload' "children[0][file][file_upload][id]=$ID"
     ```

     `pages edit` 只有加 `--allow-deleting-content` 才会删子页面和子数据库，不要随手加。

     **实测坑（2026-11-13）**：`pages create` 会忽略 Markdown 开头的属性区（frontmatter），数据库字段不会写进去。建完页面再用 `ntn api "v1/pages/<page_id>" -X PATCH -d '{"properties":{...},"icon":{...}}'` 补标题、状态、日期和图标，补完读回核对。`ntn` 的附件块追加在页面末尾，要放到顶部时用 `v1/blocks/<page_id>/children` 的 `after` 参数（见 Notion API 文档），或者整页重写时先写附件再写正文。
   - 两个都没有：停下，按 `publish.md`「没接好怎么办」告诉用户。
2. fetch 目标页面：确认页面存在、拿到当前内容快照和 page_id
3. 读本地 md 源稿全文，与页面快照 diff，判断走【增量更新】还是【全量替换】

### 第 2 步：判断更新策略

| 场景 | 策略 | 原因 |
|---|---|---|
| 页面已有本手册内容，改动 < 30% 章节 | **增量更新**（update_content 逐处替换） | 保住已上传的附件块和他人评论 |
| 新页面 / 大改版 / 页面结构乱 / 换附件 | **全量替换**（replace_content） | 增量匹配成本高于重写 |
| 只加附件 / 只改顶部下载区 | insert_content + update_content 小补丁 | 最小侵入 |

**关键坑：已保存的文件块（`notion-file-block://`）无法用 update_content 定点替换**（其内部渲染文本与 API 显示不一致）。要换附件 → 直接走全量替换，或删旧块插新块。

### 第 3 步：md → Notion 转换

按下文第二节映射表转换。速查：提示块→callout、长表格→toggle、指令→代码块、文件名包 code 防死链、锚点目录删除。

### 第 4 步：页面骨架（课程手册专用）

```text
<callout 附件下载区（绿底📦，Win/Mac 双版本需注明"选你的系统版本"）> … </callout>
<file source="file-upload://…" >Win版.zip</file>
<file source="file-upload://…" >Mac版.zip</file>
---
<callout 导语区（🎯）>标题 + 一句话卖点</callout>
<callout 原文链接（灰底🔗）>飞书/源文档链接（如有）</callout>
正文（00 章起，按映射转换）
```

### 第 5 步：写页 & 附件上传链路

**全量替换**：`update-page`，command=`replace_content`，allow_async=false，icon 一并设。超过 ~60KB 建议确认无截断后收尾。

**增量更新**：`update_content` + content_updates 数组（old_str 必须与 fetch 回来的**存储格式**逐字匹配：`**bold**` 存为 `<b>`、`` `code` `` 存为 `<code>`，中文引号原样）。匹配失败 → 重新 fetch 拿最新快照再试，禁止盲猜格式。

**附件上传三步**（zip/pdf 等，双版本物料包各传一份）：
1. `create_file_upload`（filename 带扩展名）→ 得 upload_url + 短时效 Bearer token
2. curl POST 上传（-F "file=@路径"）→ 得 `file-upload://<id>`
3. 写页时用 `<file source="file-upload://<id>">文件名</file>`；上传窗口约 1 小时，**拿到 id 后尽快置入页面**，未置入的会上传过期清掉

### 第 6 步：验证 & 收尾

1. 重新 fetch 页面顶部 100 行，确认：附件块在、callout 渲染对、无残留死链、无重复块
2. 首次推送/全量替换后，扫一遍正文里是否还有被 Notion 自动链接化的文件名（`[xxx.zip](http://%E5%B0…)` 形态）→ 有就包 code/加粗修掉
3. 把页面 ID、链接、icon、附件写进课程的 `发布记录.json`（见 `publish.md`）

## 常见错误对照

| 症状 | 原因 | 处置 |
|---|---|---|
| update_content 报 no match | old_str 用了渲染格式而非存储格式 | 重新 fetch，按 `<b>`/`<code>` 等存储格式重写 old_str |
| 正文出现 `[xxx.zip](http://%E5…)` 死链 | Notion 把文件名自动链接化 | 改为 `` `xxx.zip` `` 或 **xxx.zip** |
| 文件块替换不生效 | notion-file-block 不可定点替换 | 全量替换，或删旧插新 |
| 附件"过期不存在" | file-upload id 超时未置入 | 重新 create_file_upload → curl → 尽快写页 |
| insert 后页面顶部重复块 | 首次调用超时但实际成功 | fetch 验证，有重复则删一份 |

## 一、空行规则（最高优先级）

**换模块就空一行，文字多了让浏览器自然换行，绝不硬折行。**

1. **块与块之间永远留一个空行**：callout ↔ 段落 ↔ 表格 ↔ 代码块 ↔ 列表，切换类型时必须空行。连续块挤在一起（无空行分隔）在 Notion 渲染中可读性骤降。
2. **章节切换空行**：`## 05｜…` 与上一节的最后一行之间空一行；如果上一节结尾是 callout/表格，空行更不能省。
3. **callout 内部标题与正文空行**：`<callout>` 标签、标题行、正文行之间按规范空行，children 与标题之间必须空一行。
4. **表格前后空行**：管道表格的上一块和下一块之间各空一行，表格才能独立成块渲染。
5. **代码块前后空行**：独立成块，绝不与正文混排。
6. **禁止手动折行**：正文内容再长也写在一行里，让 Notion 前端自动换行。禁止为了"视觉对齐"在句中插换行符——源稿 md 里的手工换行（如指令文本）保留在代码块内，正文段落不要模仿。
7. **例外**：表格行与行之间、列表项之间**不空行**（它们是同一块的行）；空行只用于"块与块"之间。

## 二、md → Notion 块映射表

| md 源稿元素 | Notion 写法 | 说明 |
|---|---|---|
| `> 💡 xxx`（技巧提示） | `<callout icon="💡" color="yellow_bg">` | 前后空行 |
| `> ⚠️ xxx`（注意/安全底线） | `<callout icon="⚠️" color="orange_bg">` 或 `red_bg`（铁律用红） | 安全底线=红，一般注意=橙 |
| `> 📌 xxx`（讲师提醒） | `<callout icon="📌" color="blue_bg">` | |
| `> 🗣️ xxx`（金句引用） | `<callout icon="🗣️" color="blue_bg">` | |
| `> 🤔 xxx`（设问/思考） | `<callout icon="🤔" color="brown_bg">` | |
| `> 🎁/🎉 xxx`（彩蛋/福利） | `<callout icon="🎁" color="purple_bg">` | |
| 附件下载说明 | `<callout icon="📦" color="green_bg">` | 置于页面最顶 |
| 一句话导语 | `<callout icon="🎯" color="blue_bg">`（第1节）/ `green_bg`（第2节） | 标题+卖点两行 |
| 原文链接（飞书等） | `<callout icon="🔗" color="gray_bg">` | md 链接放 callout 内 |
| 90 分钟节奏表等长表格 | `<toggle heading="h3">标题\n\n表格\n</toggle>` | 折叠收纳，标题与表间空行 |
| 指令/提示词（``` 围栏） | 三反引号代码块原样保留 | 学员一键复制；含三反引号内容时外层用四反引号 |
| md 管道表格 | 原生管道表格 | 表头行上下必须空行 |
| `- [ ] xxx` 自评清单 | 原样保留（Notion 原生 to-do） | |
| `[📷 截图：…]` 占位 | `<span color="gray">📷 截图：…</span>` | 灰字，便于日后贴图对位 |
| `<a id="xx"></a>` 锚点 | 删除 | Notion 自带大纲，锚点无效 |
| `[⬆ 返回目录](#目录)` | 删除 | 同上 |
| `## 00｜…　\`模块①\`` | 保留 H2 + 行内 code 标签 | 模块标签保留反引号形式 |
| 手绘目录列表 | 保留为普通列表 | 每章一行，不加密链接 |

## 三、正文防死链规则

Notion 会把正文中出现的**文件名字符串**自动转换为链接（如 `小满电商-周报物料包.zip` → `[xxx.zip](http://%E5%B0…)` 死链）。防御：

1. 正文提及文件名 → 一律包 code：`` `小满电商-周报物料包.zip` ``，或加粗
2. 推送后 fetch 复查，发现 `[xxx](http://%` 形态 → update_content 替换为 code/加粗形式
3. 唯一例外：callout 里指向真实下载链接的 md 链接保留

## 四、附件（file 块）

1. `<file source="file-upload://<id>">显示名</file>` 放在附件 callout 之后、`---` 分隔线之前
2. 双版本物料包（Win/Mac）在附件 callout 里注明"选你的系统版本"，两个 file 块并列
3. 附件更新后必须重新 fetch 确认新文件块存在（id 时效、不可定点替换等坑见〇流程第 2/5 步）

## 五、验证清单（推送完成前逐项过）

- [ ] fetch 页面顶部：附件 callout + file 块 + 分隔线 + 导语 callout + 原文链接 顺序正确
- [ ] 正文无 `[xxx](http://%` 死链
- [ ] 无重复块（尤其页面顶部）
- [ ] 所有 callout 有 icon 和 color；代码块语言标记无错乱
- [ ] 表格前后有空行，渲染为原生表格
- [ ] toggle 折叠块内表格正常
- [ ] to-do 清单可勾选
- [ ] 章节标题层级：H1 不用（页面 title 已是），章=H2，小节=H3
- [ ] 块与块之间空行符合第一节规则

## 六、已推送页面

不写在这里。每门课的页面 ID、链接、所属数据库或父页面记在课程文件夹的 `发布记录.json`，更新已有页面时先读它；没有记录的课，先向用户要页面链接。
