#!/usr/bin/env python3
"""
博客封面生成工具
使用自定义 API 生成博客封面图片
配置从 ~/.config/hexo/config.yaml 读取
"""
import sys
import os
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path

# 添加脚本目录到 Python 路径，以便导入 hexo_config
sys.path.insert(0, str(Path(__file__).parent))
from hexo_config import get_api_config, load_config


def generate_cover(prompt, output_path, api_key=None, base_url=None, model=None, size=None):
    """
    使用 API 生成封面图片
    
    Args:
        prompt: 图片描述提示词
        output_path: 输出文件路径
        api_key: API 密钥（可选，优先使用配置文件）
        base_url: API 基础 URL（可选，优先使用配置文件）
        model: 模型名称（可选，优先使用配置文件）
        size: 图片尺寸（可选，优先使用配置文件）
    
    Returns:
        bool: 是否成功
    """
    # 从配置文件加载，命令行参数优先
    config = get_api_config()
    
    api_key = api_key or config.get("api_key", "")
    base_url = base_url or config.get("base_url", "")
    model = model or config.get("model", "")
    size = size or config.get("size", "")
    
    if not api_key:
        print("Error: API key 未设置。请运行以下命令配置:")
        print("  python hexo_config.py set-api-key <your-api-key>")
        print("或编辑 ~/.config/hexo/config.yaml")
        return False
    if not base_url:
        print("Error: image_api.base_url 未设置，请编辑 ~/.config/hexo/config.yaml")
        return False
    if not model:
        print("Error: image_api.model 未设置，请编辑 ~/.config/hexo/config.yaml")
        return False
    if not size:
        print("Error: image_api.size 未设置，请编辑 ~/.config/hexo/config.yaml")
        return False
    
    # 构建请求
    url = f"{base_url}/v1/images/generations"
    
    payload = {
        "prompt": prompt,
        "model": model,
        "n": 1,
        "size": size,
        "response_format": "url"  # 返回 URL 而非 base64，节省带宽
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        print(f"正在生成封面图片...")
        print(f"提示词: {prompt}")
        print(f"模型: {model}, 尺寸: {size}")
        
        # 发送请求
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        # 获取图片 URL
        if "data" in result and len(result["data"]) > 0:
            image_url = result["data"][0].get("url")
            revised_prompt = result["data"][0].get("revised_prompt", "")
            
            if revised_prompt:
                print(f"修订后的提示词: {revised_prompt}")
            
            # 下载图片
            print(f"正在下载图片...")
            urllib.request.urlretrieve(image_url, output_path)
            
            # 验证文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"[OK] 封面已保存: {output_path} ({file_size / 1024:.1f} KB)")
                return True
            else:
                print("Error: 图片下载失败")
                return False
        else:
            print(f"Error: API 返回异常: {result}")
            return False
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"Error: HTTP {e.code} - {error_body}")
        return False
    except urllib.error.URLError as e:
        print(f"Error: 网络错误 - {e.reason}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def build_cover_prompt(title, style=None):
    """
    根据博客标题构建封面提示词
    
    Args:
        title: 博客标题
        style: 风格描述（可选）
    
    Returns:
        str: 完整的提示词
    """
    config = load_config()
    default_style = config.get("image_api", {}).get(
        "default_prompt_style", 
        "cinematic tech-futuristic style, vibrant lighting, 8k resolution"
    )
    
    style = style or default_style
    
    # 构建提示词
    prompt = f"A professional blog cover image for an article titled '{title}'. "
    prompt += f"Style: {style}. "
    prompt += "The image should be visually appealing, modern, and suitable for a tech blog. "
    prompt += "No text overlay, clean composition, professional quality."
    
    return prompt


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_cover.py '<prompt>' <output_path>")
        print("       python generate_cover.py --title 'Blog Title' <output_path>")
        print("")
        print("Options:")
        print("  --title    使用标题自动生成提示词")
        print("  --style    自定义风格（与 --title 配合使用）")
        print("  --api-key  指定 API Key（优先于配置文件）")
        print("  --model    指定模型（优先于配置文件）")
        print("  --size     指定尺寸（优先于配置文件）")
        sys.exit(1)
    
    # 解析参数
    args = sys.argv[1:]
    prompt = None
    output_path = None
    title = None
    style = None
    api_key = None
    model = None
    size = None
    positional_args = []
    
    i = 0
    while i < len(args):
        if args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        elif args[i] == "--style" and i + 1 < len(args):
            style = args[i + 1]
            i += 2
        elif args[i] == "--api-key" and i + 1 < len(args):
            api_key = args[i + 1]
            i += 2
        elif args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        elif args[i] == "--size" and i + 1 < len(args):
            size = args[i + 1]
            i += 2
        else:
            positional_args.append(args[i])
            i += 1
    
    # 处理位置参数
    if title:
        # 使用 --title 时，位置参数是 output_path
        if positional_args:
            output_path = positional_args[0]
    else:
        # 不使用 --title 时，位置参数是 prompt 和 output_path
        if len(positional_args) >= 2:
            prompt = positional_args[0]
            output_path = positional_args[1]
        elif len(positional_args) == 1:
            prompt = positional_args[0]
    
    # 如果使用 --title，生成提示词
    if title:
        prompt = build_cover_prompt(title, style)
        # output_path 应该是剩余的非选项参数
        if not output_path and len(args) > 0:
            # 找到最后一个非选项参数作为 output_path
            for j in range(len(args) - 1, -1, -1):
                if not args[j].startswith('--') and j > 0 and not args[j-1].startswith('--'):
                    output_path = args[j]
                    break
                elif not args[j].startswith('--') and j == 0:
                    # 这是第一个参数且不是选项
                    pass
    
    if not prompt:
        print("Error: 需要提供 prompt 或 --title")
        sys.exit(1)
    
    if not output_path:
        print("Error: 需要提供 output_path")
        sys.exit(1)
    
    # 生成封面
    success = generate_cover(prompt, output_path, api_key=api_key, model=model, size=size)
    sys.exit(0 if success else 1)
