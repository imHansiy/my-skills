#!/usr/bin/env python3
"""
Hexo 配置管理工具
读取和保存 ~/.config/hexo/config.yaml 中的 API 配置
"""
import os
import sys
import yaml
from pathlib import Path

# 配置文件路径
CONFIG_DIR = Path.home() / ".config" / "hexo"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# 默认配置模板
DEFAULT_CONFIG = {
    "image_api": {
        "base_url": "https://ducksaymay-lumina.hf.space",
        "api_key": "",
        "model": "gpt-image-2",
        "size": "1792x1024",  # 16:9 比例，适合博客封面
        "default_prompt_style": "cinematic tech-futuristic style, vibrant lighting, 8k resolution"
    },
    "github": {
        "token": "",  # GitHub Personal Access Token
        "use_gh_cli": True  # 是否使用 gh CLI 认证（优先级高于 token）
    },
    "github_oss": {
        "repo": "imHansiy/GitHub_Oss",
        "cdn_base": "https://jsdelivr.007666.xyz/gh/imHansiy/GitHub_Oss@main"
    },
    "hexo_blog": {
        "repo": "imHansiy/MyHexo",
        "posts_path": "source/_posts"
    }
}


def ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    """加载配置文件，如果不存在则返回默认配置"""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None:
                return DEFAULT_CONFIG.copy()
            return config
    except Exception as e:
        print(f"Warning: Error reading config: {e}", file=sys.stderr)
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置到文件"""
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        print(f"Config saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"Error saving config: {e}", file=sys.stderr)
        return False


def get_api_config():
    """获取 API 配置"""
    config = load_config()
    return config.get("image_api", DEFAULT_CONFIG["image_api"])


def update_api_config(api_key=None, base_url=None, model=None, size=None):
    """更新 API 配置"""
    config = load_config()
    
    if "image_api" not in config:
        config["image_api"] = DEFAULT_CONFIG["image_api"].copy()
    
    if api_key is not None:
        config["image_api"]["api_key"] = api_key
    if base_url is not None:
        config["image_api"]["base_url"] = base_url
    if model is not None:
        config["image_api"]["model"] = model
    if size is not None:
        config["image_api"]["size"] = size
    
    return save_config(config)


def get_github_config():
    """获取 GitHub 配置"""
    config = load_config()
    return config.get("github", DEFAULT_CONFIG["github"])


def update_github_config(token=None, use_gh_cli=None):
    """更新 GitHub 配置"""
    config = load_config()
    
    if "github" not in config:
        config["github"] = DEFAULT_CONFIG["github"].copy()
    
    if token is not None:
        config["github"]["token"] = token
    if use_gh_cli is not None:
        config["github"]["use_gh_cli"] = use_gh_cli
    
    return save_config(config)


def check_config():
    """检查配置是否完整"""
    config = load_config()
    api_config = config.get("image_api", {})
    github_config = config.get("github", {})
    
    issues = []
    if not api_config.get("api_key"):
        issues.append("image_api.api_key 未设置")
    if not api_config.get("base_url"):
        issues.append("image_api.base_url 未设置")
    
    # 检查 GitHub 认证配置
    use_gh_cli = github_config.get("use_gh_cli", True)
    if not use_gh_cli and not github_config.get("token"):
        issues.append("github.token 未设置（且未使用 gh CLI）")
    
    return issues


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python hexo_config.py show              - 显示当前配置")
        print("  python hexo_config.py check              - 检查配置完整性")
        print("  python hexo_config.py set-api-key <key>  - 设置图片 API Key")
        print("  python hexo_config.py set-github-token <token> - 设置 GitHub Token")
        print("  python hexo_config.py init               - 初始化默认配置")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "show":
        config = load_config()
        print(yaml.dump(config, default_flow_style=False, allow_unicode=True))
    
    elif action == "check":
        issues = check_config()
        if issues:
            print("配置问题:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print("配置完整 [OK]")
    
    elif action == "set-api-key":
        if len(sys.argv) < 3:
            print("Usage: python hexo_config.py set-api-key <key>")
            sys.exit(1)
        key = sys.argv[2]
        if update_api_config(api_key=key):
            print(f"API Key 已保存")
        else:
            print("保存失败")
            sys.exit(1)
    
    elif action == "set-github-token":
        if len(sys.argv) < 3:
            print("Usage: python hexo_config.py set-github-token <token>")
            sys.exit(1)
        token = sys.argv[2]
        if update_github_config(token=token, use_gh_cli=False):
            print(f"GitHub Token 已保存")
        else:
            print("保存失败")
            sys.exit(1)
    
    elif action == "init":
        if CONFIG_FILE.exists():
            print(f"配置文件已存在: {CONFIG_FILE}")
            print("如需重置，请先删除该文件")
        else:
            if save_config(DEFAULT_CONFIG):
                print(f"默认配置已创建: {CONFIG_FILE}")
                print("请编辑配置文件设置 api_key")
            else:
                sys.exit(1)
    
    else:
        print(f"未知操作: {action}")
        sys.exit(1)
