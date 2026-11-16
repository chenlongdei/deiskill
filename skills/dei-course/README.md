# dei-course · AI 实操课制作

**把一份课程方案做成一节能直接上的课：学员手册、Windows 和 Mac 都能直接解压的物料包、讲师练习卡，再一键推到你常用的飞书、Notion 或钉钉。**

它是 [deiskill](https://github.com/chenlongdei/deiskill) 的一部分，也可以单独装、单独用。

## 最快拿到第一个结果

只要 Python 3.9+。装好后对你的 Agent 说：

> 我想做一节教大家用 AI 写周报的课，帮我写第 1 节课手册

没有现成方案也没关系，口述给它，它整理成方案请你确认。动笔前它会先给你看三样东西：课里的虚构场景和人物、物料清单、手册目录。

## 安装

**和装其他 Skill 一样**（需要 Node.js）：

```bash
npx -y skills add chenlongdei/deiskill --skill dei-course
```

**或者用一键安装**，它会顺便检查环境，重装时备份旧版本、保留你的配置：

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.sh | bash -s -- dei-course
```

Windows PowerShell（需要先装好 git 和 Python 3.9+）：

```powershell
$env:DEISKILL_ONLY="dei-course"; irm https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.ps1 | iex
```

不想敲命令：把这个页面的网址发给你的 Agent，说「帮我安装 `dei-course`，按 README 操作」。

它会自动识别 Claude Code、Codex、WorkBuddy 等 Agent 的 skills 目录；装好后重启 Agent。以后想要整套能力，装 [deiskill 全套](https://github.com/chenlongdei/deiskill)即可，本机配置和数据都会保留。

## 它能做什么

| 你说 | 你会拿到 |
| --- | --- |
| 「按这份方案写第 N 节课手册」 | 13 章学员手册 |
| 「做物料包和讲师卡」 | Win / Mac 两个物料包（Windows 自带解压不乱码），讲师练习卡和课后练习 |
| 「把手册推到飞书 / Notion / 钉钉」 | 平台上的课程页面链接，以及一份发布记录，下次改完直接更新同一个页面 |

## 用的是什么方法

来自四节真实上过的 AI 办公课、六轮迭代：

- **13 章固定结构**，一节 90 分钟的课分六个模块；判断标准是「初中没毕业能看懂，高学历觉得通俗」。
- **数据闭环**：物料之间的数字互相对得上（会议记录里说的数 = 表格里的数），演示数据用脚本生成并核对合计，全部标「虚构演示数据」。
- **绝不编数**：手册里的耗时、成绩、课堂数字留空，等讲师填真实记录。
- **跨课伏笔**：上一节的预估，下一节用真实数据揭晓；这一节的产出就是下一节的素材。
- **AI 生成要等，等的时候不能干等**：每个等待时间都安排了事做。
- **校对不过不发布**：数字、交叉引用、代码块逐项核对。

## 成品示例

[AI 夜校四节课](examples/AI夜校四节课/)：Word 周报、Excel 乱数据、PPT、飞书办公系统，每节有主手册、讲师卡和 Win / Mac 物料包。

## 要准备什么、花多少钱

| 需要准备 | 费用 |
| --- | --- |
| Python 3.9+ | 免费 |
| 发布时（三选一）：飞书 `lark-cli`、Notion `ntn` 或 Agent 的 Notion 连接器、钉钉 `dws` | 免费 |

## 结果存在哪里

第一次用时，它会问你「dei 工作区」放在哪里，你确认后才创建。课程在工作区的 `05_成品/课程/<课程名>/` 下；你指定了别的文件夹就用你指定的。

## 许可

MIT，见仓库根目录的 LICENSE。
