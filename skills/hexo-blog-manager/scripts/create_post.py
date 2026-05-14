#!/usr/bin/env python3
"""
Hexo 博客一键创建工具
自动化完成：配置检查 → 封面生成 → 上传 OSS → 创建 Markdown → 提交 GitHub
"""
import sys
import os
import json
import base64
import urllib.request
import urllib.error
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# 添加脚本目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))
from hexo_config import get_api_config, get_github_config, load_config, check_config
from generate_cover import generate_cover, build_cover_prompt


def run_cmd(cmd, cwd=None, check=True):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, encoding='utf-8'
        )
        if check and result.returncode != 0:
            print(f"命令执行失败: {cmd}")
            print(f"错误: {result.stderr}")
            return False
        return result
    except Exception as e:
        print(f"命令执行异常: {e}")
        return False


def check_git_auth():
    """检查 GitHub CLI 认证状态"""
    result = run_cmd("gh auth status", check=False)
    if result and result.returncode == 0:
        return True
    print("Error: GitHub CLI 未认证，请先运行 'gh auth login'")
    return False


def upload_to_oss(image_path, date_str, filename):
    """
    上传图片到 GitHub OSS
    
    Args:
        image_path: 本地图片路径
        date_str: 日期字符串 (YY-MM-DD)
        filename: 文件名
    
    Returns:
        str: CDN 链接，失败返回 None
    """
    config = load_config()
    oss_config = config.get("github_oss", {})
    repo = oss_config.get("repo", "imHansiy/GitHub_Oss")
    cdn_base = oss_config.get("cdn_base", "https://jsdelivr.007666.xyz/gh/imHansiy/GitHub_Oss@main")
    github_config = get_github_config()
    use_gh_cli = github_config.get("use_gh_cli", True)
    github_token = github_config.get("token", "")
    
    # 构建远程路径
    remote_path = f"img/{date_str}/{filename}"
    commit_message = f"oss: add {filename}"
    
    # 读取并编码图片
    with open(image_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode()
    
    # 创建 payload
    payload = {
        "message": commit_message,
        "content": content,
        "branch": "main"
    }
    
    # 写入临时文件
    temp_payload = tempfile.mktemp(suffix='.json')
    with open(temp_payload, 'w', encoding='utf-8') as f:
        json.dump(payload, f)
    
    try:
        api_path = f"/repos/{repo}/contents/{remote_path}"
        
        if use_gh_cli:
            # 使用 gh CLI
            cmd = f'gh api --method PUT {api_path} --input "{temp_payload}"'
        else:
            # 使用 GitHub Token
            if not github_token:
                print("[ERROR] GitHub Token 未设置")
                return None
            cmd = f'curl -s -X PUT "https://api.github.com{api_path}" '
            cmd += f'-H "Authorization: token {github_token}" '
            cmd += f'-H "Content-Type: application/json" '
            cmd += f'-d "@{temp_payload}"'
        
        result = run_cmd(cmd, check=False)
        
        if result and result.returncode == 0:
            cdn_link = f"{cdn_base}/{remote_path}"
            print(f"[OK] 封面已上传: {cdn_link}")
            return cdn_link
        else:
            print(f"[WARN] 上传失败，使用本地路径")
            return None
    finally:
        # 清理临时文件
        if os.path.exists(temp_payload):
            os.remove(temp_payload)


def create_markdown(title, tags=None, category=None, banner_url=None, output_dir=None):
    """
    创建博客 Markdown 文件
    
    Args:
        title: 博客标题
        tags: 标签列表
        category: 分类
        banner_url: 封面图片 URL
        output_dir: 输出目录
    
    Returns:
        str: 文件路径
    """
    # 生成文件名（URL 友好）
    slug = title.lower()
    slug = slug.replace(' ', '-')
    # 移除特殊字符，保留中文、英文、数字、连字符
    slug = ''.join(c for c in slug if c.isalnum() or c == '-' or '\u4e00' <= c <= '\u9fff')
    slug = slug.strip('-')
    if not slug:
        slug = datetime.now().strftime('%Y%m%d%H%M%S')
    
    filename = f"{slug}.md"
    
    # 确定输出目录
    if output_dir is None:
        config = load_config()
        hexo_config = config.get("hexo_blog", {})
        repo = hexo_config.get("repo", "imHansiy/MyHexo")
        posts_path = hexo_config.get("posts_path", "source/_posts")
        # 默认在当前目录创建，后续需要手动移动到 Hexo 仓库
        output_dir = "."
    
    filepath = os.path.join(output_dir, filename)
    
    # 生成 Frontmatter
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tags_str = json.dumps(tags) if tags else "[]"
    
    frontmatter = f"""---
title: {title}
date: {now}
tags: {tags_str}
categories: ["{category or '未分类'}"]
banner: {banner_url or ''}
headimg: {banner_url or ''}
---

"""
    
    # 生成内容模板
    content_template = f"""
## 引言

在这里写引言...

## 正文

在这里写正文...

## 总结

在这里写总结...

---

*如有问题，欢迎在评论区交流。*
"""
    
    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)
        f.write(content_template)
    
    print(f"[OK] 博客文件已创建: {filepath}")
    return filepath


def commit_to_github(filepath, title):
    """
    提交博客到 GitHub
    
    Args:
        filepath: Markdown 文件路径
        title: 博客标题
    
    Returns:
        bool: 是否成功
    """
    config = load_config()
    hexo_config = config.get("hexo_blog", {})
    repo = hexo_config.get("repo", "imHansiy/MyHexo")
    posts_path = hexo_config.get("posts_path", "source/_posts")
    github_config = get_github_config()
    use_gh_cli = github_config.get("use_gh_cli", True)
    github_token = github_config.get("token", "")
    
    # 复制文件到 Hexo 仓库
    hexo_repo_path = os.path.expanduser(f"~/MyHexo")  # 假设仓库在用户目录
    if not os.path.exists(hexo_repo_path):
        print(f"[WARN] Hexo 仓库路径不存在: {hexo_repo_path}")
        print(f"请手动将 {filepath} 移动到 Hexo 仓库的 {posts_path} 目录")
        return False
    
    target_path = os.path.join(hexo_repo_path, posts_path, os.path.basename(filepath))
    
    # 复制文件
    import shutil
    shutil.copy2(filepath, target_path)
    print(f"[OK] 文件已复制到: {target_path}")
    
    # 提交到 GitHub
    commit_message = f"feat: new post '{title}'"
    
    if use_gh_cli:
        # 使用 gh CLI
        cmd = f'cd "{hexo_repo_path}" && git add . && git commit -m "{commit_message}" && git push'
    else:
        # 使用 GitHub Token（通过 git 凭证）
        if not github_token:
            print("[ERROR] GitHub Token 未设置")
            return False
        # 设置远程 URL 包含 token
        remote_url = f"https://x-access-token:{github_token}@github.com/{repo}.git"
        cmd = f'cd "{hexo_repo_path}" && git remote set-url origin {remote_url} && git add . && git commit -m "{commit_message}" && git push'
    
    result = run_cmd(cmd, check=False)
    
    if result and result.returncode == 0:
        print(f"[OK] 已提交到 GitHub")
        return True
    else:
        print(f"[WARN] 提交失败，请手动提交")
        return False


def create_blog(title, tags=None, category=None, skip_cover=False, skip_upload=False, 
                auto_commit=False, output_dir=None):
    """
    一键创建博客
    
    Args:
        title: 博客标题
        tags: 标签列表
        category: 分类
        skip_cover: 跳过封面生成
        skip_upload: 跳过封面上传
        auto_commit: 自动提交到 GitHub
        output_dir: 输出目录
    
    Returns:
        bool: 是否成功
    """
    print("=" * 60)
    print(f"[START] 开始创建博客: {title}")
    print("=" * 60)
    
    # Step 1: 检查配置
    print("\n[Step 1/5] 检查配置...")
    issues = check_config()
    if issues:
        print(f"配置问题: {', '.join(issues)}")
        print("请先运行: python hexo_config.py set-api-key <your-api-key>")
        return False
    print("[OK] 配置完整")
    
    # Step 2: 生成封面
    banner_url = None
    cover_path = None
    
    if not skip_cover:
        print("\n[Step 2/5] 生成封面图片...")
        date_str = datetime.now().strftime('%y-%m-%d')
        cover_filename = f"cover-{datetime.now().strftime('%H%M%S')}.png"
        cover_path = os.path.join(tempfile.gettempdir(), cover_filename)
        
        # 生成封面
        success = generate_cover(
            prompt=build_cover_prompt(title),
            output_path=cover_path
        )
        
        if not success:
            print("[WARN] 封面生成失败，继续创建博客...")
            cover_path = None
        else:
            print(f"[OK] 封面已生成: {cover_path}")
            
            # 用户确认（在实际使用中，这里应该暂停等待用户确认）
            print("[TIP] 提示: 请检查封面图片，如需重新生成请使用 --skip-cover 参数跳过")
    else:
        print("\n[Step 2/5] 跳过封面生成")
    
    # Step 3: 上传封面到 OSS
    if cover_path and not skip_upload:
        print("\n[Step 3/5] 上传封面到 OSS...")
        date_str = datetime.now().strftime('%y-%m-%d')
        banner_url = upload_to_oss(cover_path, date_str, cover_filename)
        
        # 清理本地封面文件
        try:
            os.remove(cover_path)
            print(f"[OK] 临时文件已清理")
        except:
            pass
    else:
        print("\n[Step 3/5] 跳过封面上传")
    
    # Step 4: 创建 Markdown 文件
    print("\n[Step 4/5] 创建博客 Markdown...")
    filepath = create_markdown(
        title=title,
        tags=tags,
        category=category,
        banner_url=banner_url,
        output_dir=output_dir
    )
    
    # Step 5: 提交到 GitHub
    if auto_commit:
        print("\n[Step 5/5] 提交到 GitHub...")
        commit_to_github(filepath, title)
    else:
        print("\n[Step 5/5] 跳过自动提交")
        print(f"[TIP] 请手动将 {filepath} 移动到 Hexo 仓库并提交")
    
    # 完成
    print("\n" + "=" * 60)
    print("[DONE] 博客创建完成!")
    print("=" * 60)
    print(f"[FILE] 文件: {filepath}")
    if banner_url:
        print(f"[COVER] 封面: {banner_url}")
    print(f"\n[NEXT] 下一步:")
    print(f"   1. 编辑 {filepath} 撰写内容")
    print(f"   2. 移动到 Hexo 仓库的 source/_posts/ 目录")
    print(f"   3. 运行 'hexo generate && hexo deploy' 发布")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Hexo 博客一键创建工具')
    parser.add_argument('--title', '-t', required=True, help='博客标题')
    parser.add_argument('--tags', help='标签，用逗号分隔')
    parser.add_argument('--category', '-c', help='分类')
    parser.add_argument('--skip-cover', action='store_true', help='跳过封面生成')
    parser.add_argument('--skip-upload', action='store_true', help='跳过封面上传')
    parser.add_argument('--auto-commit', action='store_true', help='自动提交到 GitHub')
    parser.add_argument('--output', '-o', help='输出目录')
    
    args = parser.parse_args()
    
    # 处理标签
    tags = None
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',')]
    
    # 创建博客
    success = create_blog(
        title=args.title,
        tags=tags,
        category=args.category,
        skip_cover=args.skip_cover,
        skip_upload=args.skip_upload,
        auto_commit=args.auto_commit,
        output_dir=args.output
    )
    
    sys.exit(0 if success else 1)
