---
name: odoo-docs-manager
description: 自动将 Odoo 模块文档（README.md/docs）映射为 `static/description/index.html` 的文档管理工具。支持自动总结模块功能并生成精美的介绍页面。
---

# Odoo 文档管理技能 (Odoo Docs Manager)

本技能旨在帮助 Odoo 开发者自动管理模块的介绍页面。它可以将项目中的 Markdown 文档转换为 Odoo 官方应用市场风格的 HTML 介绍页。

## 核心工作流

### 1. 识别模块与文档源
- **定位 Odoo 模块**：确认当前操作的目录是否包含 `__manifest__.py`。
- **确定文档来源**：
    - **显式指定**：如果用户提供了具体的 Markdown 文件路径，直接使用该文件。
    - **自动查找**：如果用户未指定，按顺序查找：`/docs/README.md`、`/docs/index.md`、`/dos/README.md` (处理拼写错误) 或根目录下的 `README.md`。
    - **智能总结**：若无任何 Markdown 文档，则执行“智能总结”：
        1. 读取 `__manifest__.py` 了解模块基本信息（名称、摘要、分类、版本、依赖）。
        2. 扫描模块目录结构（模型、视图、静态资源）。
        3. 自行生成一份结构化的 `docs/AUTO_SUMMARY.md`。

### 2. Markdown 转换
- **使用工具**：优先使用 `npx markdown-to-html-cli`。
- **转换指令参考**：
  ```bash
  npx markdown-to-html-cli --source <SOURCE_MD> --output static/description/index.html
  ```
- **样式增强与视觉卓越**：
    - 确保生成的 HTML 包含基础 CSS，且符合 Odoo 的 `description` 规范。
    - **视觉美感**：生成的页面必须展现出“高级感”。使用优雅的字体（如 Inter）、和谐的色调（避免纯红纯蓝，使用带灰度的品牌色）、平滑的边框圆角以及清晰的层次感。
    - **内容结构**：自动插入带有微交互感（通过 CSS hover）的卡片式布局来展示“核心功能”。
    - **响应式**：确保在 Odoo 后台的不同屏幕宽度下均有良好表现。

### 3. 美化与进阶 (可选)
- **图片处理**：如果 Markdown 中引用了本地图片，尝试将其转换为 Base64 或确保路径在 `static/description` 下可用。
- **Odoo 品牌化**：在生成的 Markdown 中自动加入“Features”、“Installation”、“Usage”等标准 H2 标题。

## 执行准则
1. **优先确认**：在执行转换前，先通过 `ls` 或 `list_dir` 确认文档源的存在。
2. **宁缺毋滥**：如果需要智能总结，生成的 Markdown 必须包含：
    - 模块标题
    - 单句摘要 (Summary)
    - 核心功能点列表 (Features)
    - 依赖说明 (Dependencies)
3. **静默执行**：除非遇到无法解决的冲突，否则直接生成并反馈结果。
