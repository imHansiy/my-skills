# Odoo Docs Manager Skill

这是一个专为 Odoo 开发者设计的技能，用于简化模块介绍页面的维护。

## 功能特性
- **一键转换**：支持将 `docs/README.md` 转换为 Odoo 规范的 `static/description/index.html`。
- **智能纠错**：支持识别 `dos` 文件夹（防误点）。
- **智能总结**：在缺失文档时，自动根据 `__manifest__.py` 和模块结构生成功能介绍。
- **外观精美**：生成的 HTML 页面具备良好的排版和 Odoo 品牌适配感。

## 使用方法
1. **开发者触发**：当你在 Odoo 模块目录下工作时，可以要求我“使用 odoo-docs-manager 技能生成介绍页”。
2. **自定义路径**：你可以指明特定的文档地址，例如：“把 `docs/module_overview.md` 转成模块介绍”。
3. **完全自动化**：如果你只是说“帮我生成这个模块的介绍页”，我会自动寻找或生成内容。

## 依赖工具
- `npx` (Node.js 环境)
- `markdown-to-html-cli` (通过 npx 运行)
