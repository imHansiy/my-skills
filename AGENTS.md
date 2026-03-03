# My Skills Spec Guide

本文件用于说明本仓库内 **Agent Skills** 的格式规范（基于 `agentskills.io/specification`），并明确哪些字段是必填。

> 说明：`agents.md` 规范本身是 AGENTS.md 的通用说明文件格式（自由 Markdown）；
> 本文聚焦于你仓库中 `skills/` 下每个 Skill 的编写标准。

---

## 1) 仓库建议结构

```text
my-skills/
├─ AGENTS.md
├─ README.md
└─ skills/
   ├─ my-template-skill/
   │  ├─ SKILL.md          # 必填
   │  ├─ metadata.json     # 可选
   │  ├─ README.md         # 可选
   │  ├─ scripts/          # 可选
   │  ├─ references/       # 可选
   │  └─ assets/           # 可选
   └─ another-skill/
      └─ SKILL.md
```

---

## 2) 每个 Skill 的最低要求（必填）

每个 skill 目录中，**至少必须有一个 `SKILL.md`**。

`SKILL.md` 必须是：
1. YAML Frontmatter（开头 `---` 到结束 `---`）
2. 后接 Markdown 正文（技能说明）

### Frontmatter 必填字段

| 字段 | 是否必填 | 规则 |
|---|---|---|
| `name` | 是 | 1-64 字符；仅小写字母/数字/连字符 `-`；不能以 `-` 开头或结尾；不能有 `--`；**必须与父目录同名** |
| `description` | 是 | 1-1024 字符；不能为空；应说明“做什么 + 何时触发” |

---

## 3) 可选字段（推荐按需使用）

| 字段 | 是否必填 | 说明 |
|---|---|---|
| `license` | 否 | 许可证名称或引用许可证文件 |
| `compatibility` | 否 | 环境要求（例如依赖命令、网络权限、适用平台），最长 500 字符 |
| `metadata` | 否 | 任意键值元信息（如 author/version/tags） |
| `allowed-tools` | 否 | 预授权工具列表（空格分隔，实验特性，支持度视代理实现而定） |

---

## 4) 标准 SKILL.md 模板

```yaml
---
name: my-template-skill
description: Standardize responses with a fixed execution structure. Use when users ask for workflow-style outputs, consistent task breakdowns, or reusable delivery checklists.
license: MIT
metadata:
  author: imHansiy
  version: "0.1.0"
---
```

````markdown
# My Template Skill

## When to Apply
- ...

## Execution Rules
1. ...

## Output Template
```text
[Goal]
- ...
```
````

---

## 5) 正文（Markdown）推荐写法

虽然正文没有强制字段，但建议至少包含：
- 适用场景（When to Apply）
- 执行步骤（Step-by-step）
- 输入/输出示例
- 常见边界情况（Edge Cases）

建议主 `SKILL.md` 控制在约 500 行以内；长文档拆到 `references/`。

---

## 6) 可选目录规范

- `scripts/`：可执行脚本（Python/Bash/JS 等）
- `references/`：补充说明文档（按需读取）
- `assets/`：模板、图片、静态数据

引用路径建议使用相对路径（从 skill 根目录出发），并避免过深嵌套。

---

## 7) 发布前自检清单（必看）

1. `skills/<目录名>/SKILL.md` 是否存在（必填）
2. `name` 是否与目录名完全一致（必填）
3. `name` 是否符合字符规则（必填）
4. `description` 是否完整描述“做什么 + 何时触发”（必填）
5. 可选字段如 `allowed-tools` 是否与你使用的代理兼容（建议）

可使用参考校验工具：

```bash
skills-ref validate ./skills/my-template-skill
```
