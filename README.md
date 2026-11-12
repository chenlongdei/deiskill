# deiskill

一套覆盖日常「输入 → 处理 → 输出」的中文 AI Skills。安装到 Claude Code、Codex、WorkBuddy 等支持 Skills 的 Agent 后，在对话里直接使用。

## 安装

```bash
git clone https://github.com/chenlongdei12-dev/deiskill.git
cd deiskill
bash scripts/install.sh                 # 检测本机已有的 Agent；有多个时会问你装到哪些
bash scripts/install.sh --list          # 查看全部 Skill
bash scripts/install.sh --target ~/.claude/skills --target ~/.workbuddy/skills   # 指定目录
bash scripts/install.sh dei-daily-report   # 只装指定的 Skill
```

覆盖安装时：

- 旧版本整体备份到 `~/.deiskill/backups/<时间>/`；
- 各 Skill 里的 `data/`、`config.json`、`agent.conf` 等本机状态自动保留；
- 上游 Skill 和依赖从上游仓库现拉，不存放在本仓库。

## 全部 Skill

### 输入

| Skill | 用途 |
| --- | --- |
| `dei-daily-report` | 政策、AI、知乎、抖音的综合日报与按领域日报 |
| `dei-capture` | YouTube 关键词搜索、频道视频清单、单视频逐字稿（yt-dlp 为主，TikHub、本地 Whisper 兜底） |

### 处理

| Skill | 用途 |
| --- | --- |
| `dei-notebook` | 用 NotebookLM 把文档和 YouTube 视频建成知识库；7 个问题做出学习计划和面向应用的实操手册，或主题研究综述；生成简体中文音频、思维导图 |

### 总入口

| Skill | 用途 |
| --- | --- |
| `dei` | 从想要的最终交付倒推，串联上面的 Skill；收尾可把文档同步到飞书或 Notion |

### 处理（上游 Skill，安装时从 [dbskill](https://github.com/dontbesilent2025/dbskill) 拉取）

| Skill | 用途 |
| --- | --- |
| `dbs-diagnosis` | 判断商业问题是否成立，或全面检查一门生意 |
| `dbs-learning` | 把一个课题拆成连续的学习文章，按反馈调整下一篇 |
| `dbs-chatroom` | 请几位专家角色围绕一个话题分别发言，最后汇总 |
| `dbs-deconstruct` | 拆解一个说不清的概念，讲清它在不同场合的意思 |

dbs 系列版权归 dontbesilent 所有，仅安装自用，本仓库不包含其文件。

### 输出

规划中。

## 模板

| 文件 | 用途 |
| --- | --- |
| [templates/dei-选题表.xlsx](templates/dei-选题表.xlsx) | 选题策划表：开头、主体叙事、结尾、主标题、选题理由、内容策划，以及点赞、评论、收藏、转发 |

## 配置

Skill 不预设你电脑上有哪些文件夹。第一次运行时会询问保存位置或输入文件并给出建议，确认后帮你创建目录并写入该 Skill 的 `config.json`；之后不再重复问。报告和运行数据放在你选的位置，不放在 Agent 的 skills 安装目录里。凭证类配置见各 Skill 的 `config.example.json`。`config.json` 不进 Git。

## 维护

- 规范：[docs/skill-spec.md](docs/skill-spec.md)
- 自有 Skill 登记在 [catalog.json](catalog.json)，上游内容登记在 [external.json](external.json)
- 修改后运行 `python3 scripts/validate_repo.py`
