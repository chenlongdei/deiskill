# deiskill 管理约定

这个文件夹是 deiskill 的唯一维护位置（GitHub：chenlongdei12-dev/deiskill）。新增、修改、删除 Skill 都在这里做，改完再安装到 Agent。

## 常用操作

```bash
python3 scripts/validate_repo.py        # 每次修改后必跑
bash scripts/install.sh --list          # 查看全部 Skill
bash scripts/install.sh                 # 检测本机 Agent 并安装（覆盖安装会保留本机配置与凭证）
bash scripts/install.sh <skill-name>    # 只装一个
```

## 规则

- 写或改 Skill 前先读 [docs/skill-spec.md](docs/skill-spec.md)：命名、`dei-handoff`、正文骨架、叶子不点名、首次运行询问保存位置。
- 自有 Skill 放 `skills/<name>/` 并登记 `catalog.json`；上游内容登记 `external.json`，不把文件提交进来。
- 不在仓库里写本机绝对路径、凭证或个人草稿；需要本机路径的写进 Skill 的 `config.json`（不进 Git）。
- Skill 要能装在 Claude Code、Codex、WorkBuddy 等任意 Agent 上；不写死某个 Agent 的目录或命令，用用户实际使用的或指定的。
- commit 前跑校验；推到公开仓库前确认没有本机路径、凭证和个人草稿。
