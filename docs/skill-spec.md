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
- **不假设用户有任何文件夹或文件。** 需要保存位置或输入文件时，首次运行询问用户并给出建议值；目录不存在时说明完整路径、确认后再创建；写入 `config.json` 后不再重复问。`config.example.json` 里的路径留空，不放作者本机的默认值。
- 已配置的路径失效时（换电脑、云盘未同步），说明哪一项失效并请用户决定，不静默新建。无人值守运行时，缺配置的部分标为不可用，其余照常执行。
- 凭证只来自 `config.json` 或环境变量，不打印、不写入产物、不进 Git。
- 报告、原始数据和状态放在用户确认的保存位置下，不写进 Agent 的 skills 安装目录；脚本没有配置时报错退出，不静默落到安装目录。仅凭证类 `config.json` 留在 Skill 目录，安装器覆盖安装时自动保留。
- 不假设用户用哪个 Agent，不写死任何 Agent 的目录或命令。用户用哪个 Agent 安装、运行，就用哪个；用户指定了目录或命令，就用指定的；需要无头运行或定时时先确认实际使用的 Agent。

## 7. 第三方内容

- 许可证允许再分发（如 MIT）的，保留原 LICENSE 一起提交。
- 没有许可证或禁止再分发的（如 dbskill、follow-builders），登记在 `external.json`，由 `scripts/install.sh` 安装时从上游拉取。
