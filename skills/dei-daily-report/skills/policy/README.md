# 新闻联播：政策与商机日报（v3.3）

把新闻联播中简略的报道，整理成普通读者能理解、能继续验证的政策与商机分析。核心方法：**以假设为驱动，以事实为基础，提出符合逻辑的真知灼见。**

新闻不预设AI或其他行业优先；报告以事实和经济机制选择重点。分析使用部署它的agent，抓取不需要专用API Key，但agent本身可能计费或消耗账户额度。

## 方法如何工作

1. **去粗取精：**读当天全文，快讯逐项拆开，筛出真正改变需求、成本、规则的事情。
2. **去伪存真：**查发布机关文件、官方解读和历史正文，同时找支持与反证；不是只搜能证明直觉的材料。
3. **由表及里：**解释谁的具体问题改变了、为什么可能付钱、钱从哪里来、交付和利润在哪里。
4. **由此及彼：**研究上下游、受损方向和替代方案，分清政策执行链与同主题关联。
5. **提出并更新假设：**先提出可检验判断，公开资料由agent查找并读取；需要访谈和实践的部分给明确问题与停止条件。
6. **形成洞察：**今日结论说明事实背后的因果关系，不能把报道标题和数字拼成总结。跨日保留主题和判断，证据变了就更新。

完整方法在[analysis-method.md](references/analysis-method.md)，正反例在[examples.md](references/examples.md)。无需原课程附件或作者机器资料。

## 成品结构

- 今日结论：判断、事实、因果解释、边界。
- 全部新闻信号：S/A/B/C分组，组内按重要性，保留原编号；以文字展开。
- 边际变化：五列表格——事项、过去、现在、变化判断、经营含义。
- 商机假设：数量按独立机会自然形成；写事实支持、相反解释、买方、付费、交付、成本、门槛、验证。
- 受损方向与连续追踪。
- 已取得资料与下一步现实验证：准确链接、可下载原件、未取得材料分清。

政策级别与商机成熟度分开：政策A级不代表订单可进入。重复报道不算新政策；新查到旧资料是研究更新，不能冒充当天变化。预算、销售额、资本投资、贷款和累计交易量不得混用。格式检查不代表内容或外部审核必然通过。

## 最快部署：交给现有agent

本模块随 `dei-daily-report` 一起安装，不单独复制。在 deiskill 仓库根目录运行：

```bash
bash scripts/install.sh dei-daily-report
```

覆盖安装会自动保留本模块的 `data/` 和 `agent.conf`。其他 agent 用 `--target <skills目录>` 指定安装位置；不支持自动发现 skills 时，直接让它读取本目录的 SKILL.md。

给agent的任务：

> 读取 dei-daily-report/skills/policy/SKILL.md，按完整方法生成昨天的政策与商机日报。全文拆快讯、核验公开文件、回溯历史、提出并检验假设。边际变化用表格，其他文字展开。将报告写入data/报告并给链接。

需要文件读写、Python 3.9+、curl，以及联网检索、网页/PDF读取能力。网络工具由目标agent提供，不绑定某个MCP。没有检索能力时只能输出明确标注限制的分析，不能声称已外部核验。Python需可用Asia/Shanghai时区数据；最小Linux环境按系统方式安装时区数据库。

## 无头CLI部署（macOS/Linux）

```bash
cd <安装目录>/dei-daily-report/skills/policy
bash install.sh                  # 只检查环境、建数据目录
bash install.sh --backfill       # 可选：回填最近31期，不调用模型
bash scripts/run_daily.sh        # 抓取昨日及缺失历史，调用agent生成
bash scripts/run_daily.sh --date 2026-09-13  # 指定播出日
bash scripts/run_daily.sh --date 2026-09-13 --force  # 备份后重做
```

脚本默认取Asia/Shanghai昨日，历史按此前30个自然日逐日补齐，不用最新一期顶替昨日。目标日抓取失败返回非零并输出日志位置，历史缺失交给agent明确披露。此行为尚不包含任何邮件、消息平台发送。

`run_agent.sh`依次使用本地`agent.conf`、Claude Code CLI、Codex CLI。自动探测需要CLI已安装并登录。其他CLI配置：

```bash
cp agent.conf.example agent.conf
```

编辑AGENT_CMD为实际可用的非交互命令。协议是从stdin接收任务，在skill根目录读写。示意命令不是对某个未测试CLI的兼容保证；需要自己安装后试跑。agent.conf是本地可信shell配置，会执行配置中的命令，不放密钥到GitHub。

Codex默认以workspace-write运行；外部检索、网络与工具权限按该CLI实际配置提供。不能为了自动化就假定具有浏览能力。模型执行默认超时1800秒，可用`XWLB_AGENT_TIMEOUT`修改；并发通过文件锁避免重复运行。报告包含方法版本标识，同版报告跳过，旧版或force会备份到revisions。脚本不自动打开报告。

## 每天05:00定时：只选一套

**agent自带调度（推荐已有此能力时）：**时区Asia/Shanghai，每日05:00，任务为读取SKILL.md并完整生成昨日晨报。新报告、失败或需要处理时通知，状态不变安静。复制skill不会自动复制或创建作者的定时任务。

**macOS launchd（可选）：**

```bash
bash install.sh --launchd
# 需要立即试跑时另外执行：
bash scripts/run_daily.sh
# 移除本脚本创建的调度：
bash uninstall.sh
```

launchd使用系统时区，安装检查当前UTC+8，使用此方案须保持系统为Asia/Shanghai。安装时保存当前PATH以寻找CLI；搬移目录或CLI路径改变后重新安装。不要同时启用agent调度与launchd。脚本不会主动唤醒关机机器；休眠、CLI登录、网络与权限可影响执行。Linux可由现有调度器以Asia/Shanghai每日05:00调用run_daily.sh，调度器需捕获非零退出并通知。

## 数据、迁移与升级

```text
SKILL.md                      方法入口
references/analysis-method.md 完整方法
references/examples.md        提炼后的正反例
references/automation-prompt.md 可复制定时任务
templates/daily-report.md    成品模板
scripts/fetch_xwlb.py          标准库抓取
scripts/run_daily.py           日期、历史、去重与执行
scripts/run_daily.sh           CLI入口
scripts/run_agent.sh           agent适配
install.sh / uninstall.sh      初始化与可选调度
agent.conf.example             命令配置示例
data/                          运行生成，Git忽略
```

data 指 dei 工作区的 `03_日报/政策与商机/`。逐字稿`data/逐字稿/YYYY/MM/YYYYMMDD.md`，报告`data/报告/YYYY/YYYY-MM-DD_分析报告.md`，原件`data/原件/YYYY/播出日/`，主题`data/主题状态.json`，修订`data/修订/`，日志在工作区`99_系统/日志/政策与商机/`。升级复制代码方法模板，保留已有data和agent.conf；跨设备迁移需要另行复制运行数据并检查自己的调度配置。

本包不包含私人日报、完整课程逐字稿、密钥或任务ID。来源为第三方文字稿，关键事实须主动回到原始发布核验。方法形成的商业判断是假设，不保证付费需求或回报。

## 验证

```bash
python3 -m unittest discover -s tests -v
```

覆盖嵌套HTML正文、日期校验、抓取失败状态和晨报流程。真实agent的联网核验与模型输出质量需在目标环境首次试跑确认。
