# My Agent Skills

用于集中管理我自己的多个 Agent Skills，方便统一维护与安装。

参考格式：<https://github.com/vercel-labs/agent-skills>

## 仓库结构

```text
my-skills/
├─ skills/
│  └─ my-template-skill/
│     ├─ SKILL.md
│     ├─ README.md
│     └─ metadata.json
└─ README.md
```

## 如何新增一个 Skill

1. 在 `skills/` 下新建目录，例如：`skills/my-debug-skill/`
2. 至少提供一个 `SKILL.md`
3. 可选补充 `README.md`、`metadata.json`、`scripts/`、`references/`

## 安装方式（发布到 GitHub 后）

```bash
npx skills add <your-github-username>/my-skills
```

如果你只想安装单个 skill，请按你使用的工具文档指定路径安装。
