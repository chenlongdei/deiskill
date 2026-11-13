# deiskill Skill 规范

新增或迁移 Skill 时按本文执行，并运行 `python3 scripts/validate_repo.py`。

## 1. 分层

deiskill 按「输入 → 处理 → 输出」组织日常工作：

| 层 | 做什么 | 例子 |
| --- | --- | --- |
| `router` | 总入口，根据目标选择和组合 Skill | `dei` |
| `input` | 把外部信息拿进来：采集、转写、检索、日报 | `dei-daily-report`、`dei-capture` |
| `process` | 理解、提问、诊断、学习 | `dei-notebook`、上游 dbs 方法 Skill |
| `output` | 把结论变成可发布的成品 | 后续补充 |

分层登记在 `catalog.json` 的 `layer` 字段，只用于导航和组合，不限制 Skill 能做什么。

## 2. 命名与目录

- 自有 Skill 统一使用 `dei-` 前缀和小写 kebab-case，目录名与 frontmatter `name` 一致，放在 `skills/<name>/`。
- 上游 Skill 保留原名，只登记在 `external.json`，不把文件放进本仓库。
- 一个能力只有一个维护位置。同一件事（例如抖音转写）不在两个 Skill 里各写一套脚本。

## 3. frontmatter

```yaml
---
name: dei-xxx
description: 做什么。什么时候用；不用于什么。
metadata:
  dei-handoff: |
    - <接手时的状态> → <交出的东西>
    - <另一种接手状态> → <交出的东西>
    - 不交出：<容易被误以为会做、其实不做的事>
---
```

- `description` 只写用途和触发时机，一到三句；不写案例细节、完整流程或命令。
- `dei-handoff` 每行一条「接手 → 交出」，最后一行以「不交出：」开头。`dei` 依靠它从最终交付倒推组合，description 只用来初筛。
- handoff 只写正文里真实存在的能力；正文改了，按「正文 → handoff → description」的顺序同步。

## 4. 正文骨架

按需取用，顺序保持一致：

1. **使命**：一两句说清这个 Skill 解决什么。
2. **铁律**：用户明确反馈过、必须遵守的规则。
3. **流程**：Step 0 先读已有材料和配置，再按步骤执行；references 写明「在哪一步读」，不一次性全部加载。
4. **缺少信息时**：能判断就给带条件的判断；必须问时一次问清，并说明为什么会改变结果。
5. **边界与停止条件**：凭证错误、余额不足、限流、外部授权等情况下怎样停。
6. **输出**：产物位置和格式。
7. **禁止事项**。
8. **统一结尾**（见下一节）。

## 5. 叶子 Skill 不点名其他 Skill

Skill 之间的关系只由 `dei` 掌握。叶子 Skill 结尾使用固定句：

> 完成当前任务后直接结束。用户的请求超出本 Skill 范围，或询问下一步时，用一句话说明还需要哪种能力，不点名其他 Skill；当前环境已经安装 `dei` 时，补一句「可以用 `$dei` 继续」。

例外：把另一个 Skill 当作工具依赖调用时可以点名，登记在 `scripts/validate_repo.py` 的 `NAMING_ALLOWLIST` 中。

## 6. 本机配置与隐私

- 仓库里不出现 `/Users/...`、`/Volumes/...` 等本机路径。路径、账号、工作簿位置写进 Skill 自己的 `config.json`，仓库只提交 `config.example.json`。
- **不假设用户有任何文件夹或文件。** 保存位置统一用 dei 工作区（见 6a），只在第一次问一次；需要输入文件时，首次运行询问用户并给出建议值；目录不存在时说明完整路径、确认后再创建；写入 `config.json` 后不再重复问。`config.example.json` 里的路径留空，不放作者本机的默认值。
- 已配置的路径失效时（换电脑、云盘未同步），说明哪一项失效并请用户决定，不静默新建。无人值守运行时，缺配置的部分标为不可用，其余照常执行。
- 凭证只来自 `config.json` 或环境变量，不打印、不写入产物、不进 Git。
- 报告、原始数据和状态放在用户确认的保存位置下，不写进 Agent 的 skills 安装目录；脚本没有配置时报错退出，不静默落到安装目录。仅凭证类 `config.json` 留在 Skill 目录，安装器覆盖安装时自动保留。
- 不假设用户用哪个 Agent，不写死任何 Agent 的目录或命令。用户用哪个 Agent 安装、运行，就用哪个；用户指定了目录或命令，就用指定的；需要无头运行或定时时先确认实际使用的 Agent。

## 6a. dei 工作区（用户数据的统一结构）

所有自有 Skill 的产出放在**一个**用户确认的根目录下，叫 dei 工作区。位置记在 `~/.deiskill/config.json` 的 `workspace_root`，与 Agent 无关。解析、命名、运行总账都由 `scripts/dei_workspace.py` 负责：每个自有 Skill 的 `scripts/` 里放一份，内容完全一致（Skill 分别安装、互相看不到；校验器会检查）。改它时改 `dei-capture` 那份，再复制到其他 Skill。

### 一级目录

```text
<dei 工作区>/
├── .dei-workspace     标记文件
├── 使用说明.md         init 时生成，告诉用户每个文件夹放什么
├── 01_我的清单/        用户手动维护、Skill 只读的表
├── 02_采集/            输入：dei-capture
├── 03_日报/            处理：dei-daily-report
├── 04_知识库/          处理：dei-notebook
├── 05_成品/            输出：输出层 Skill
└── 99_系统/            运行总账.jsonl、日志/、状态/、备份/、测试/、缓存/
```

- **编号规则**：01—05 按「输入 → 处理 → 输出」的顺序排；99 永远排在最后，放用户平时不用看的东西。这和用户自己文件夹常见的 `01_… 02_… 90_… 99_…` 写法一致。新增阶段接着编 06；必须插在中间时，用迁移脚本统一改编号，不手工改。
- 一级目录按阶段分，不按 Skill 名分。新 Skill 只是在某个阶段里多一个二级文件夹。

### 二级、三级命名

| 层级 | 规则 | 例子 |
| --- | --- | --- |
| 二级 | 平台名或模块名，中文为主，不加编号 | `YouTube`、`抖音`、`政策与商机`、`知乎热榜` |
| 三级·对象型 | 长期跟踪的对象按名字命名，不带日期，内容往里累加 | `抖音/博主/<博主名>/`、`YouTube/频道/Claude/`、`04_知识库/<主题>/` |
| 三级·批次型 | 一次性运行命名为 `YYYY-MM-DD_HHMM_主题`（北京时间），只占一层；重名加 `-2` | `YouTube/搜索/2026-11-11_2326_Claude-Code入门/` |
| 高频批次 | 一天可能跑一次以上的（日报、知乎热榜），先按年分一层 | `03_日报/综合/2026/2026-11-13_1058/` |
| 模块内部子目录 | 一律中文：`逐字稿`、`报告`、`原件`、`原始采集`、`修订`、`线索`、`主题状态.json` | `03_日报/政策与商机/报告/2026/` |

- 批次和对象文件夹的**第一层只放人看的文件**（报告、清单、逐字稿、成品）；机器数据（原始 JSON、状态库）放进 `_原始数据/`。
- 用 `dei_workspace.batch_dir()` 建批次文件夹，用 `dei_workspace.now()` 取北京时间，不自己拼时间戳。

### 规则

- **不静默新建**：根目录下没有 `.dei-workspace` 就报错停下（外接盘没挂载时，macOS 会在原路径悄悄建本地文件夹，数据就写错了地方）。只有 `dei_workspace.py init` 会创建工作区，而且要用户先确认路径。
- **运行总账**：每次运行结束调用 `dei_workspace.log_run(skill, 任务, 状态, 产出路径)`（Agent 执行的步骤用 `python3 scripts/dei_workspace.py log ...`），写进 `99_系统/运行总账.jsonl`。`dei` 靠它找最近的产出。
- **试跑与测试**：设环境变量 `DEI_TRIAL=1`，产出改写到 `99_系统/测试/`，运行总账标 `trial`。正式目录里不出现 `_试跑`、`_测试` 文件夹。单元测试用各 Skill 的旧式环境变量（如 `DEI_CAPTURE_DATA_DIR`、`DEI_CAPTURE_CONFIG`）隔离，设了它们就不碰真实工作区。
- **日志、状态、备份**放 `99_系统/日志|状态|备份/<模块>/`；`99_系统/缓存/` 里 30 天前的文件会被自动清理，不要把需要长期保留的东西放进去。
- **用户维护的表**放 `01_我的清单/`。Skill 的 `templates/` 里以「模板.xlsx」结尾的文件，`init` 时复制进去（去掉「模板」二字）。
- **工作区里不放代码**；不放凭证，凭证在各 Skill 自己的 `config.json`。
- 各 Skill `config.json` 里旧的 `output_root` 只作为单独指定位置的覆盖项保留，留空即用工作区，首次配置时不主动问。
- 音视频原文件不落地：下载、转写用临时目录，用完即删，只留逐字稿和原链接。
- 改结构（改名、改编号、改子目录）时同时更新 `scripts/migrate_workspace.py` 的映射，让已有用户能一条命令迁过去。

## 7. 第三方内容

- 许可证允许再分发（如 MIT）的，保留原 LICENSE 一起提交。
- 没有许可证或禁止再分发的（如 dbskill、follow-builders），登记在 `external.json`，由 `scripts/install.sh` 安装时从上游拉取。

## 跨平台（macOS / Windows / Linux，任意 Agent）

学员的电脑、系统和 Agent 都不确定，新增或修改 Skill 时遵守：

- **不写死 Agent 和路径**：命令写成相对 Skill 目录的 `python3 scripts/...`，并在 SKILL.md 说明 Windows 上通常换成 `python`。用户数据放在首次运行时确认的 dei 工作区（见 6a）。
- **编码一律 UTF-8**：读写文件写 `encoding="utf-8"`；`subprocess` 用 `text=True` 时同时写 `encoding="utf-8", errors="replace"`；入口脚本开头加统一的 UTF-8 输出片段（搜 `PYTHONUTF8` 可看到现成写法），让它调用的 Python 工具也用 UTF-8。
- **不用系统专属命令**：需要 `open`、`launchctl` 之类时按 `sys.platform` 分支，并给出 Windows 和 Linux 的做法；时区用固定偏移（北京时间 = UTC+8），不依赖 Windows 默认没有的时区数据库。
- **依赖按需安装**：每个 Skill 有自检命令，缺依赖时按用户系统给出一条安装命令（macOS 用 brew、Windows 用 winget、Linux 用 apt 或 pip），用户同意后再执行。安装说明写在 Skill 自己的 references 里，因为装好的 Skill 看不到仓库根目录。
- **模板、案例放在 Skill 目录里**（`templates/`、`examples/`），会随 Skill 一起安装；SKILL.md 或 references 要写明何时去看它们。
