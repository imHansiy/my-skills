# 海灵正文配图 Skill

把中文文章、业务知识、技术教程、Odoo 内容和方法论，转换成简洁、有趣、带海风与茶温度的白底手绘图。

## 主要特征

- 固定角色“海灵”：蓝色浪发、橙色海星、白蓝斗篷、茶杯意象。
- 16:9 纯白极简手绘，大量留白。
- 海洋蓝、浅青与少量珊瑚橙。
- 海灵必须参与核心动作，而不是装饰性讲解员。
- 默认一图一个认知锚点；支持 2–4 场景的轻教程总览。
- 当用户生成、改写、扩写或整理中文文章、博客、Markdown、Notion 正文、教程和复盘时，默认参与配图规划与生成；用户明确不要配图时除外。
- 包含角色参考图、提示词模板、构图规则、QA 清单和验证脚本。

## 安装

解压后，将整个 `hailing-illustrations` 目录复制到用户技能目录：

```bash
mkdir -p "$HOME/.agents/skills"
cp -R ./hailing-illustrations "$HOME/.agents/skills/"
```

项目内使用时，也可以放到仓库的：

```text
.agents/skills/hailing-illustrations/
```

Codex 未立即显示时，重启 Codex。

## 使用

```text
Use $hailing-illustrations 为这篇中文文章规划并生成 5 张海灵正文配图。
```

```text
Use $hailing-illustrations 写一篇中文技术博客，并自动生成 2 张正文配图。
```

```text
Use $hailing-illustrations 为“Odoo 销售到收款”生成一张简洁的一图看懂教程。
```

```text
Use $hailing-illustrations 先不要生图，只输出 shot list。
```

更多范例见 `examples/prompts.md`。

## 目录

```text
hailing-illustrations/
├── SKILL.md
├── agents/openai.yaml
├── assets/
│   ├── character/hailing-character-sheet.png
│   ├── examples/
│   ├── icon-small.png
│   └── icon-large.png
├── references/
├── examples/prompts.md
├── scripts/validate_skill.py
├── LICENSE
└── NOTICE.md
```

## 验证

```bash
python scripts/validate_skill.py
```

验证会检查必需文件、技能名称、角色资产和旧角色关键词残留。

## 校准资产

`assets/character/` 用于锁定角色身份。`assets/examples/` 仅用于低频校准简洁度、留白和角色参与方式，不是可复刻模板。

## 许可

本包保留上游 MIT 许可与署名，并加入本次海灵定制内容。详见 `LICENSE` 和 `NOTICE.md`。
