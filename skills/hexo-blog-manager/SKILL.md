---
name: hexo-blog-manager
description: |
  Manage the user's configured Hexo blog repository and configured image-hosting repository through GitHub CLI (`gh`) against online repositories by default. Use when Codex needs to create or update Hexo posts, generate or replace blog covers, generate or revise blog article content, upload images and write CDN links, fix Hexo post frontmatter or rendering issues, configure the Hexo blog workflow, or commit/push blog changes. Always read repository names, paths, CDN base URLs, image generation settings, and blog content style from `~/.config/hexo/config.yaml`; prefer GitHub Contents API operations over looking for local files, local clones, or broad local git staging.
---

# Hexo Blog & OSS Resource Manager Skill

This skill defines the standard operating procedure (SOP) for managing the Hexo blog repository and image-hosting repository configured in `~/.config/hexo/config.yaml`.

## Critical Guardrails

- Read `~/.config/hexo/config.yaml` before deciding repository names, CDN base URLs, posts paths, API base URLs, models, or image sizes. Do not hardcode a specific blog repository, OSS repository, CDN host, or local checkout path.
- Operate online-first with `gh`. Do not look for the user's local Hexo repo, clone repositories, or edit local blog files unless the user explicitly asks for local work. Treat the configured `hexo_blog.repo` and `github_oss.repo` as the source of truth.
- Read and update GitHub files with `gh api /repos/<owner>/<repo>/contents/<path>` or `gh api --method PUT ... --input <payload.json>`. For updates, fetch the current file SHA first and include it in the PUT payload.
- Local disk use is allowed only for temporary generated artifacts, API payload JSON, or inspection scratch files needed to call `gh api`; clean them up after successful upload/update.
- Treat `create_post.py --auto-commit` as unsafe for an existing dirty repository: it may stage broad changes with `git add .`. Prefer manual git commands, stage only task-related files, and inspect `git status --short` before and after every Hexo generation step.
- `hexo generate`, `hexo server`, and plugin validation can rewrite frontmatter in unrelated posts, especially `abbrlink`, YAML array formatting, and folded URLs. If the user did not ask for those changes, restore those files before committing.
- Do not commit generated `public/`, `db.json`, temporary payload JSON, generated cover previews, or unrelated frontmatter churn unless the user explicitly asks for them.
- When fixing rendering, verify both build output and browser behavior. For Mermaid, checking that Hexo produced `<div class="mermaid">` is not enough; the active theme must load Mermaid JS and run initialization after first load and PJAX navigation.
- For image uploads, upload binary assets to the configured `github_oss.repo`, verify the uploaded file exists or the CDN URL resolves, then update `banner` and `headimg`.
- Before using Hexo-specific syntax in a post, identify the installed third-party plugins from the online `package.json` and Hexo config files. Use the plugin's documented tag/filter/frontmatter syntax instead of inventing Markdown or HTML.
- Before generating or rewriting article body content, read the configured `blog_content` style settings. Do not impose a fixed writing style from this skill when `blog_content` is empty; ask the user or infer from existing posts only when appropriate.

## Configuration

### 配置文件位置
- **路径**: `~/.config/hexo/config.yaml`
- **首次使用**: 运行 `python <SKILL_PATH>/scripts/hexo_config.py init` 创建默认配置

### 配置结构
```yaml
image_api:
  base_url: "<image-api-base-url>"                 # API 地址
  api_key: "your-api-key-here"                      # API 密钥（必填）
  model: "<image-model>"                            # 图片生成模型
  size: "<image-size>"                              # 图片尺寸（建议 16:9）
  default_prompt_style: "cinematic tech-futuristic style, vibrant lighting, 8k resolution"

github:
  token: "ghp_xxxxxxxxxxxx"      # GitHub Personal Access Token
  use_gh_cli: true                # 是否使用 gh CLI 认证（优先级高于 token）

github_oss:
  repo: "<owner>/<image-repo>"
  cdn_base: "https://cdn.example.com/gh/<owner>/<image-repo>@main"

hexo_blog:
  repo: "<owner>/<hexo-repo>"
  posts_path: "source/_posts"

blog_content:
  style_prompt: ""                 # 正文写作风格总提示词；为空时不要硬套固定风格
  audience: ""                     # 目标读者，例如 小白/开发者/运维/产品用户
  tone: ""                         # 语气，例如 直接、技术博客、教程式、复盘式
  structure: []                    # 推荐章节结构；为空时按主题自然组织
  language: "zh-CN"                # 正文语言
  requirements: []                 # 固定要求，例如 多用示例、避免营销腔、保留代码块
```

### GitHub 认证方式

支持两种认证方式（按优先级）：

| 方式 | 配置 | 说明 |
|------|------|------|
| **gh CLI**（默认） | `use_gh_cli: true` | 使用 `gh auth login` 的 OAuth token |
| **Personal Access Token** | `token: "ghp_xxx"` | 直接使用 GitHub PAT |

#### 使用 gh CLI（推荐）
```bash
# 先登录 GitHub CLI
gh auth login

# 配置自动使用 gh CLI
python hexo_config.py show  # 确认 use_gh_cli: true
```

#### 使用 GitHub Token
```bash
# 设置 GitHub Personal Access Token
python hexo_config.py set-github-token ghp_xxxxxxxxxxxxxxxxxxxx
```

**Token 权限要求**：
- `repo` - 完整仓库访问权限
- `workflow` - 如果需要触发 GitHub Actions

### 配置管理命令
```bash
# 查看当前配置
python <SKILL_PATH>/scripts/hexo_config.py show

# 检查配置完整性
python <SKILL_PATH>/scripts/hexo_config.py check

# 设置图片 API Key
python <SKILL_PATH>/scripts/hexo_config.py set-api-key <your-api-key>

# 设置 GitHub Token（如果不使用 gh CLI）
python <SKILL_PATH>/scripts/hexo_config.py set-github-token <your-github-token>

# 初始化默认配置
python <SKILL_PATH>/scripts/hexo_config.py init
```

---

## 本地草稿脚本（可选）

默认不要使用本地脚本直接改博客仓库。只有当用户明确要求生成本地草稿、临时预览或离线编辑时，才使用 `create_post.py`。

### 命令格式
```bash
python <SKILL_PATH>/scripts/create_post.py --title "博客标题" [选项]
```

### 选项参数
| 参数 | 说明 | 示例 |
|------|------|------|
| `--title`, `-t` | 博客标题（必填） | `--title "Python 入门教程"` |
| `--tags` | 标签，逗号分隔 | `--tags "Python,编程,教程"` |
| `--category`, `-c` | 分类 | `--category "编程"` |
| `--skip-cover` | 跳过封面生成 | `--skip-cover` |
| `--skip-upload` | 跳过封面上传 | `--skip-upload` |
| `--auto-commit` | 自动提交到 GitHub；仅适合全新、干净、专用输出目录，不要在已有 Hexo 仓库中默认使用 | `--auto-commit` |
| `--output`, `-o` | 输出目录 | `--output ./posts` |

### 使用示例
```bash
# 基础用法（生成封面 + 创建 Markdown）
python <SKILL_PATH>/scripts/create_post.py --title "我的第一篇博客"

# 完整用法（仅限全新专用输出目录；已有仓库优先手动 stage/commit）
python <SKILL_PATH>/scripts/create_post.py \
  --title "Python 异步编程指南" \
  --tags "Python,异步,编程" \
  --category "技术" \
  --output ./drafts

# 跳过封面（快速创建）
python <SKILL_PATH>/scripts/create_post.py \
  --title "快速笔记" \
  --skip-cover \
  --output ./drafts
```

### 本地脚本流程
```
┌─────────────────────────────────────────────────────────┐
│  Step 1: 检查配置                                        │
│  → 验证 API Key 和配置完整性                             │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: 生成封面图片                                    │
│  → 调用 AI API 生成 16:9 封面                            │
│  → 保存到临时目录                                        │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: 上传封面到 OSS                                  │
│  → 上传到配置的图片仓库                                 │
│  → 获取 CDN 链接                                         │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: 创建本地 Markdown 草稿                          │
│  → 生成带 Frontmatter 的 .md 文件                        │
│  → 包含标题、日期、标签、封面链接                         │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Step 5: 上传到 GitHub（使用 gh api 推荐）               │
│  → 读取线上目标路径和 SHA                               │
│  → PUT 到 GitHub Contents API                           │
│  → 验证线上文件                                         │
└─────────────────────────────────────────────────────────┘
```

### 首次配置流程
1. 运行 `python <SKILL_PATH>/scripts/hexo_config.py init` 创建配置文件
2. 提示用户提供 API Key
3. 运行 `python <SKILL_PATH>/scripts/hexo_config.py set-api-key <key>` 保存
4. 验证配置: `python <SKILL_PATH>/scripts/hexo_config.py check`

---

## Workflow

### 0. Online GitHub Workflow (Default)

Use this workflow unless the user explicitly asks to work in a local checkout:

1. Identify the target repo and path:
   - `BLOG_REPO`: read from `hexo_blog.repo`
   - `OSS_REPO`: read from `github_oss.repo`
   - `POSTS_PATH`: read from `hexo_blog.posts_path`
   - `CDN_BASE`: read from `github_oss.cdn_base`
   - Post path: `$POSTS_PATH/<post>.md`
2. Read online content with `gh api`:
   ```bash
   gh api /repos/$BLOG_REPO/contents/$POSTS_PATH/post.md --jq ".content" | base64 -d
   ```
   Also capture `.sha` before updating:
   ```bash
   gh api /repos/$BLOG_REPO/contents/$POSTS_PATH/post.md --jq ".sha"
   ```
3. Write updates with a JSON payload and the current SHA:
   ```json
   {
     "message": "fix(blog): update post frontmatter",
     "content": "<base64-encoded-new-file>",
     "sha": "<current-file-sha>",
     "branch": "main"
   }
   ```
   ```bash
   gh api --method PUT /repos/$BLOG_REPO/contents/$POSTS_PATH/post.md --input payload.json
   ```
4. Upload images to `$OSS_REPO` the same way, but omit `sha` when creating a new file.
5. Verify online state with `gh api` after every write. Do not assume a local file reflects GitHub.

### 1. Local Draft Script (Optional)
Only use `create_post.py` when the user explicitly wants a local draft. For normal blog work, create or update the online file through the GitHub workflow above:
```bash
python <SKILL_PATH>/scripts/create_post.py --title "博客标题" --tags "标签1,标签2" --category "分类" --output ./drafts
```
已有 Hexo 仓库中不要默认使用 `--auto-commit`；脚本的提交逻辑会复制文件并 broad-stage，容易混入无关文件。

---

### 2. Image Preparation & Upload (Image Hosting Flow)
When a Hexo post requires an image (screenshot, diagram, asset):
- **Target Repository**: read from `github_oss.repo`.
- **Target Path**: `img/YY-MM-DD/filename.extension` unless config or the user specifies another asset convention.
- **Steps**:
    1. Read the image file and encode it to Base64.
    2. Write a JSON payload containing `{"message": "...", "content": "..."}` to a temporary file.
    3. Execute the upload using `gh api --method PUT ... --input temp.json`.
    4. Verify the uploaded file with `gh api /repos/$OSS_REPO/contents/img/YY-MM-DD/filename.extension`.
- **CDN Link Format**: `$CDN_BASE/img/YY-MM-DD/filename.extension`, where `CDN_BASE` comes from config.

### 3. Blog Cover Generation (AI-Powered)
To make the Hexo blog post list look more professional and textured, generate a cover image using the configured API:

- **Service**: read `image_api.base_url` and `image_api.api_key` from `~/.config/hexo/config.yaml`.
- **Model**: read `image_api.model` from config.
- **Size**: read `image_api.size` from config; use 16:9 when the config does not specify a size.
- **Output rule**: generate an image file locally only as a temporary artifact, upload it to the configured image repository with `gh api`, then update the online Hexo post with the configured CDN URL using `gh api`.
- **Prompt rule**: build the prompt from the post title, category, tags, and topic. Ask for a 16:9 blog cover, no text overlay, no UI mockups unless the post is about an interface, and a concrete visual metaphor tied to the article. Avoid generic "tech background" prompts.

#### Steps:
1. **Check Configuration**: Verify API config is complete:
   ```bash
   python <SKILL_PATH>/scripts/hexo_config.py check
   ```
   If not configured, guide user to set up API key.

2. **Generate Image**: Run the script with title or custom prompt:
   ```bash
   # Using blog title (auto-generates professional prompt)
   python <SKILL_PATH>/scripts/generate_cover.py --title "Your Blog Title" cover.png
   
   # Using custom prompt
   python <SKILL_PATH>/scripts/generate_cover.py "A futuristic tech workspace with holographic displays" cover.png
   
   # With custom style
   python <SKILL_PATH>/scripts/generate_cover.py --title "Your Title" --style "minimalist, dark theme" cover.png
   ```
   If the default generated prompt is too generic, use a custom prompt. For example:
   ```bash
   python <SKILL_PATH>/scripts/generate_cover.py "16:9 editorial tech blog cover for a Go project bypassing AWS anti-bot detection: Chrome TLS fingerprint visualization, browser fingerprint signals, AWS cloud gateway, clean cinematic composition, no text overlay" cover.png
   ```

3. **User Review (Mandatory)**: Show the generated `cover.png` to the user and **wait for user confirmation** before proceeding. If the user is not satisfied, adjust the prompt and regenerate.

4. **Store Assets**: Only after user approval, upload the image to the configured image repository:
   - Run: `python <SKILL_PATH>/scripts/upload_prep.py cover.png "oss: add blog cover"`
   - Execute: `gh api --method PUT /repos/$OSS_REPO/contents/img/YY-MM-DD/cover.png --input temp_payload.json`

5. **Environment Cleanup**: After a successful upload, you **must delete** all locally generated image files, temporary JSON files, and any temporary scripts used during the process.

6. **Update Online Post Frontmatter**: Fetch the target post from the configured blog repository, preserve existing frontmatter, replace only `banner` and `headimg`, and PUT the updated file back with its current SHA.

- **Frontmatter Setup**: Add or update the `banner: <CDN_LINK>` and `headimg: <CDN_LINK>` fields to configure the cover display in the Hexo environment.

### 4. Create or Update Hexo Blog Post
- **Target Repository**: read from `hexo_blog.repo`.
- **Target Path**: `$POSTS_PATH/your-post-title.md`, where `POSTS_PATH` is read from `hexo_blog.posts_path`.
- **Default Edit Method**: use `gh api` to read the online file, update content, and PUT it back with the current SHA. Do not search local checkout paths unless explicitly requested.
- **Content Style**: before generating or rewriting body content, read `blog_content` from config and apply `style_prompt`, `audience`, `tone`, `structure`, `language`, and `requirements`.
- **Frontmatter Specification**: Must contain header information compliant with Hexo standards:
  ```yaml
  ---
  title: Post Title
  date: YYYY-MM-DD HH:mm:ss
  tags: [Tag1, Tag2]
  categories: [Category1]
  banner: <CDN_LINK>
  headimg: <CDN_LINK>
  ---
  ```
- **Image Referencing Convention**: The body of the article must **always use** CDN links constructed from configured `github_oss.cdn_base`.

### 5. Generate or Rewrite Blog Content

Use this workflow when creating a new article body, expanding a draft, rewriting a section, or adapting generated content to the user's blog:

1. Read `blog_content` from `~/.config/hexo/config.yaml`.
2. If `blog_content.style_prompt` is present, treat it as the primary writing instruction.
3. Apply optional fields:
   - `audience`: choose depth, terminology, and explanation level.
   - `tone`: control voice and sentence style.
   - `structure`: use the configured section order unless the user asks otherwise.
   - `language`: write in that language.
   - `requirements`: enforce each listed rule.
4. If `blog_content` is empty and the user did not provide style instructions, do not invent a house style. Ask for style preferences when the task is mostly writing; for small edits, preserve the existing article's voice.
5. Preserve technical accuracy and plugin syntax. Do not replace valid code fences, tag plugin blocks, frontmatter fields, or image links while rewriting prose.
6. For tutorial posts, prefer concrete examples, runnable commands when relevant, and short explanations before abstractions. Avoid marketing filler unless `blog_content` requests it.

### 6. Identify Third-Party Hexo Plugins and Syntax

Use this workflow before adding tag plugins, diagrams, encrypted sections, math, media embeds, galleries, custom frontmatter, or any syntax that is not plain Markdown:

1. Read the online dependency list:
   ```bash
   gh api /repos/$BLOG_REPO/contents/package.json --jq ".content" | base64 -d
   ```
   Identify Hexo plugins from dependency names such as `hexo-tag-*`, `hexo-filter-*`, `hexo-generator-*`, `hexo-renderer-*`, and theme packages.
2. Read the online config that enables or configures plugins:
   ```bash
   gh api /repos/$BLOG_REPO/contents/_config.yml --jq ".content" | base64 -d
   gh api /repos/$BLOG_REPO/contents/_config.volantis.yml --jq ".content" | base64 -d
   ```
3. Search online posts for existing examples before inventing syntax. Substitute config-derived values before running the query:
   ```bash
   gh api /search/code -f q="repo:<BLOG_REPO> \"{% mermaid %}\" path:<POSTS_PATH>"
   gh api /search/code -f q="repo:<BLOG_REPO> \"markmap\" path:<POSTS_PATH>"
   ```
4. If syntax is still uncertain, fetch the plugin's README or official docs and use that exact syntax. Do not guess tag names or closing tags.
5. Apply the plugin syntax to the post and verify output. Examples:
   - `hexo-tag-mermaid`: use `{% mermaid %}` ... `{% endmermaid %}`; do not wrap the block in triple backticks.
   - Normal code blocks: use triple backticks; never close a normal code block with `{% endmermaid %}`.
   - Volantis/theme runtime: if a plugin emits placeholders such as `<div class="mermaid">`, verify the active theme loads the required browser runtime.

### 7. Fix Hexo Rendering Issues

Use this workflow when the user reports that a post renders incorrectly:

1. Fetch the Markdown source from GitHub with `gh api`; inspect the fetched content for unbalanced fences, tag plugins, raw HTML, and escaped text. Use local search only on temporary fetched content, not on a local repo.
2. Identify the relevant third-party plugin and syntax using the plugin workflow above.
3. If browser/build verification requires local generation, use a temporary checkout or explicit user-approved local path. After any local generation, do not commit local side effects; push the final source fix through `gh api`.
4. For Mermaid specifically:
   - Normal code fences must close with triple backticks, never `{% endmermaid %}`.
   - Mermaid tag blocks must be balanced: `{% mermaid %}` ... `{% endmermaid %}`.
   - If generated HTML contains `<div class="mermaid">...</div>` but the page still shows source text, the active theme is missing Mermaid runtime initialization. Inject Mermaid JS in the active Hexo config and add a small initializer that runs on `DOMContentLoaded` and `pjax:complete`.
   - Quote labels containing nested brackets, colons, arrows, braces, slashes, or quotes, for example `A["bin[0] = 12000"]` and `B["获取信号量: sem <- struct{}{}"]`.
5. Verify in a browser, not only by reading generated HTML. Confirm plugin output is transformed as intended; for Mermaid, `document.querySelectorAll('.mermaid svg').length` should match the number of Mermaid blocks and `.error-icon` count should be zero.

## Rules & Best Practices

- **Atomic Commits**: Use descriptive commit messages, such as `oss: add screenshot for post X` or `feat: new hexo post about Y`.
- **GH CLI First**: Use `gh api` or other `gh` commands against online repositories by default. Do not browse or depend on local repository state unless explicitly requested.
- **Manual Staging**: In existing repositories, stage explicit paths only. Never rely on `git add .` when Hexo generation may rewrite unrelated posts.
- **Generation Side Effects**: After running Hexo commands, treat unrelated frontmatter changes as build side effects and revert them unless requested.
- **Base64 Encoding**: Always encode binary files (like images) into Base64 format before transmitting them via `gh api`.
- **Bypassing Command Line Limits**: Avoid passing huge Base64 strings directly as command-line arguments; always save them to a temporary JSON file and pass them using the `--input` argument.
- **Result Verification**: After uploading, verify that the file successfully exists via `gh api` before officially writing the image link into the Hexo post.
- **Configuration First**: Always check configuration before using image generation features. Prompt user for API key if not configured.
- **Plugin Syntax First**: Before using nonstandard Markdown, identify the active Hexo plugin and its syntax from online `package.json`, config, examples, or official docs.

## Applicable Scenarios
This is a **Hexo-专用 (Hexo-dedicated)** skill. Whenever the user mentions:
- Publishing a blog post
- Adding an article to Hexo
- Uploading a cover for a Hexo article
- Adding an image to the OSS hosting
- Configuring Hexo blog settings

This skill should be triggered and applied.
