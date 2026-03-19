"""
Prompt 加载服务

从独立的 Prompt 文件加载模板，支持变量替换
"""
import os
import re
from functools import lru_cache
import structlog

logger = structlog.get_logger()

# Prompt 文件目录
PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'prompts'
)


@lru_cache(maxsize=32)
def load_prompt(prompt_name: str) -> str:
    """
    加载 Prompt 文件（带缓存）
    
    Args:
        prompt_name: Prompt 文件名（不含 .txt 后缀）
        
    Returns:
        str: Prompt 模板内容
        
    Raises:
        FileNotFoundError: Prompt 文件不存在
    """
    file_path = os.path.join(PROMPTS_DIR, f"{prompt_name}.txt")
    
    if not os.path.exists(file_path):
        logger.error(f"Prompt file not found: {file_path}")
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    logger.debug(f"Loaded prompt: {prompt_name} ({len(content)} chars)")
    return content


def render_prompt(prompt_name: str, **kwargs) -> str:
    """
    加载并渲染 Prompt 模板
    
    使用安全的变量替换，避免 JSON 花括号冲突
    
    Args:
        prompt_name: Prompt 文件名（不含 .txt 后缀）
        **kwargs: 模板变量
        
    Returns:
        str: 渲染后的 Prompt
    """
    template = load_prompt(prompt_name)
    
    # 使用正则表达式替换 {variable} 格式
    rendered = template
    for key, value in kwargs.items():
        # 替换 {key} 为值
        pattern = r'\{' + re.escape(key) + r'\}'
        rendered = re.sub(pattern, str(value), rendered)
    
    logger.debug(f"Rendered prompt: {prompt_name} with {len(kwargs)} variables")
    return rendered


def list_prompts() -> list:
    """
    列出所有可用的 Prompt 文件
    
    Returns:
        list: Prompt 文件名列表（不含 .txt 后缀）
    """
    if not os.path.exists(PROMPTS_DIR):
        return []
    
    prompts = []
    for file in os.listdir(PROMPTS_DIR):
        if file.endswith('.txt'):
            prompts.append(file[:-4])  # 移除 .txt 后缀
    
    return sorted(prompts)


def get_prompt_info(prompt_name: str) -> dict:
    """
    获取 Prompt 文件信息
    
    Args:
        prompt_name: Prompt 文件名
        
    Returns:
        dict: Prompt 信息 {name, path, size, exists}
    """
    file_path = os.path.join(PROMPTS_DIR, f"{prompt_name}.txt")
    
    return {
        'name': prompt_name,
        'path': file_path,
        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        'exists': os.path.exists(file_path)
    }
