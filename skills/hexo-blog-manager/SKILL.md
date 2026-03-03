---
name: hexo-blog-manager
description: Handles the creation workflow for Hexo blog posts and the uploading of images/covers to GitHub_Oss using the jsDelivr CDN. Use exclusively for publishing or updating Hexo blog content with images.
compatibility: opencode
---

# Hexo Blog & OSS Resource Manager Skill

This skill defines the standard operating procedure (SOP) dedicated to managing blog posts in the `imHansiy/MyHexo` repository and the associated static assets / image hosting in the `imHansiy/GitHub_Oss` repository.

## Workflow

### 1. Image Preparation & Upload (Image Hosting Flow)
When a Hexo post requires an image (screenshot, diagram, asset):
- **Target Repository**: `imHansiy/GitHub_Oss`
- **Target Path**: `img/YY-MM-DD/filename.extension` (Use the current date to categorize files).
- **Steps**:
    1. Read the image file and encode it to Base64.
    2. Write a JSON payload containing `{"message": "...", "content": "..."}` to a temporary file.
    3. Execute the upload using `gh api --method PUT ... --input temp.json`.
- **CDN Link Format**: `https://jsdelivr.007666.xyz/gh/imHansiy/GitHub_Oss@main/img/YY-MM-DD/filename.extension`

### 2. Blog Cover Generation (AI-Powered)
To make the Hexo blog post list look more professional and textured, generate a cover image using Hugging Face Hub:
- **Service**: Hugging Face Inference API (depends on the `huggingface_hub` Python library).
- **Default Model**: `black-forest-labs/FLUX.1-schnell` (This model performs best for text rendering and realism).
- **Steps**:
    1. **Prompt Construction**: Generate a detailed English prompt based on the Hexo blog title. For example: "A cinematic 16:9 blog cover for [TITLE], tech-futuristic style, vibrant lighting, 8k resolution". If text rendering is needed, use: "In the center, a sign that says '[SHORT_TITLE]'".
    2. **Generate Image**: Run the accompanied Python script: `python <SKILL_PATH>/scripts/generate_cover.py "[PROMPT]" cover.png`.
    3. **User Review (Mandatory)**: Show the generated `cover.png` to the user and **wait for user confirmation** before proceeding. If the user is not satisfied, adjust the prompt and regenerate.
    4. **Store Assets**: Only after user approval, upload the image to the `GitHub_Oss` repository:
        - Run: `python <SKILL_PATH>/scripts/upload_prep.py cover.png "oss: add blog cover"`
        - Execute: `gh api --method PUT /repos/imHansiy/GitHub_Oss/contents/img/YY-MM-DD/cover.png --input temp_payload.json`
    5. **Environment Cleanup**: After a successful upload, you **must delete** all locally generated image files, temporary JSON files, and any temporary scripts used during the process.
- **Frontmatter Setup**: Add the `banner: <CDN_LINK>` and `headimg: <CDN_LINK>` fields to the Hexo post's metadata (Frontmatter) to configure the cover display in the Hexo environment.

### 3. Create or Update Hexo Blog Post
- **Target Repository**: `imHansiy/MyHexo`
- **Target Path**: `source/_posts/your-post-title.md`
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
- **Image Referencing Convention**: The body of the article must **always use** the jsDelivr CDN links constructed in Step 1.

## Rules & Best Practices

- **Atomic Commits**: Use descriptive commit messages, such as `oss: add screenshot for post X` or `feat: new hexo post about Y`.
- **Base64 Encoding**: Always encode binary files (like images) into Base64 format before transmitting them via `gh api`.
- **Bypassing Command Line Limits**: Avoid passing huge Base64 strings directly as command-line arguments; always save them to a temporary JSON file and pass them using the `--input` argument.
- **Result Verification**: After uploading, verify that the file successfully exists via `gh api` before officially writing the image link into the Hexo post.

## Applicable Scenarios
This is a **Hexo-专用 (Hexo-dedicated)** skill. Whenever there is a mention of publishing a blog post, adding an article to Hexo, uploading a cover for a Hexo article, or adding an image to the OSS hosting, this skill should be triggered and applied.
