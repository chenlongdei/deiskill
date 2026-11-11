# deiskill

一套覆盖日常「输入 → 处理 → 输出」的中文 AI Skills。安装到 Codex、Claude Code、WorkBuddy 等支持 Skills 的 Agent 后，在对话里直接使用。

## 安装

```bash
git clone https://github.com/chenlongdei12-dev/deiskill.git
cd deiskill
bash scripts/install.sh                 # 默认装到 ~/.codex/skills
bash scripts/install.sh --list          # 查看全部 Skill
bash scripts/install.sh --target ~/.claude/skills --target ~/.workbuddy/skills
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

## 配置

需要本机路径或凭证的 Skill 带有 `config.example.json`。复制为 `config.json` 后填写；`config.json` 不进 Git。

## 维护

- 规范：[docs/skill-spec.md](docs/skill-spec.md)
- 自有 Skill 登记在 [catalog.json](catalog.json)，上游内容登记在 [external.json](external.json)
- 修改后运行 `python3 scripts/validate_repo.py`
