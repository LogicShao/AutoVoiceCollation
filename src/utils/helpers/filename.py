"""
文件名处理工具模块

提供文件名安全化和智能标题生成功能
"""

import re

from src.services.llm.factory import query_llm
from src.services.llm.models import LLMQueryParams
from src.services.llm.prompts import get_prompt
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    将字符串转换为安全的文件名

    处理逻辑：
    1. 移除或替换非法字符（Windows: <>:"/\\|?* 等）
    2. 移除前后空格
    3. 将连续空格替换为单个空格
    4. 限制长度（默认 200 字符，避免路径过长）
    5. 处理空字符串情况

    Args:
        filename: 原始文件名
        max_length: 最大长度限制（默认 200）

    Returns:
        str: 安全的文件名

    Examples:
        >>> sanitize_filename("如何使用 Claude Code?")
        '如何使用 Claude Code'
        >>> sanitize_filename("C:\\\\Users\\\\test")
        'C_Users_test'
        >>> sanitize_filename("  测试  文件  ")
        '测试 文件'
    """
    if not filename:
        return "未命名"

    # 移除前后空格
    filename = filename.strip()

    # 定义非法字符（Windows + Unix）
    # Windows: < > : " / \\ | ? *
    # Unix: /
    illegal_chars = r'[<>:"/\\|?*]'

    # 替换非法字符为下划线
    safe_name = re.sub(illegal_chars, "_", filename)

    # 将连续的下划线替换为单个
    safe_name = re.sub(r"_+", "_", safe_name)

    # 将连续的空格替换为单个
    safe_name = re.sub(r"\s+", " ", safe_name)

    # 移除前后空格（再次处理，因为替换后可能产生新的空格）
    safe_name = safe_name.strip()

    # 移除前后下划线（处理非法字符替换后产生的边界下划线）
    safe_name = safe_name.strip("_")

    # 如果处理后为空，使用默认名称
    if not safe_name:
        return "未命名"

    # 限制长度（考虑中文字符，按字符数而非字节数）
    if len(safe_name) > max_length:
        # 智能截断：尝试在空格处截断
        truncated = safe_name[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.8:  # 如果空格位置在后 20% 范围内
            safe_name = truncated[:last_space]
        else:
            safe_name = truncated

    return safe_name


def generate_title_from_text(
    text: str,
    llm_service: str = "gemini-2.0-flash",
    max_length: int = 50,
    timeout: int = 10,
) -> str | None:
    """
    通过 LLM 根据文本内容生成合适的标题

    Args:
        text: 转录文本（会自动截取前 2000 字符）
        llm_service: LLM 服务名称（默认使用快速模型 Gemini Flash）
        max_length: 生成标题的最大长度（默认 50 字符）
        timeout: 超时时间（秒，默认 10 秒）

    Returns:
        str: 生成的标题（已安全化），如果失败则返回 None

    Raises:
        不会抛出异常，失败时返回 None 并记录日志

    Examples:
        >>> text = "这是一段关于机器学习的讲座内容..."
        >>> title = generate_title_from_text(text)
        >>> print(title)  # "机器学习基础讲座"
    """
    if not text or not text.strip():
        logger.warning("文本为空，无法生成标题")
        return None

    try:
        # 截取文本前 2000 字符（约 500-1000 tokens）
        text_sample = text[:2000].strip()

        prompt_spec = get_prompt("title")
        prompt = prompt_spec.render_user(text=text_sample, max_length=max_length)

        # 创建查询参数
        logger.info(f"使用 {llm_service} 生成标题...")
        params = LLMQueryParams(
            content=prompt,  # 使用 content 而不是 prompt
            system_instruction=prompt_spec.render_system(),
            api_server=llm_service,  # 使用 api_server 而不是 llm_server
            temperature=0.3,  # 使用较低的 temperature 以获得更确定的结果
            max_tokens=100,  # 标题一般很短
        )

        # 调用 LLM 生成标题（同步）
        response = query_llm(params)

        # 清理响应
        if response:
            # 移除可能的引号、换行符等（逐个处理避免 B005）
            title = response.strip()
            # 移除双引号
            title = title.strip('"')
            # 移除单引号
            title = title.strip("'")
            # 移除中文引号
            title = title.strip('"').strip('"')
            title = title.strip(""").strip(""")
            # 最终去除空格
            title = title.strip()

            # 安全化文件名
            safe_title = sanitize_filename(title, max_length=max_length)

            logger.info(f"生成标题成功: {safe_title}")
            return safe_title

        logger.warning("LLM 返回空响应")
        return None

    except Exception as e:
        logger.error(f"标题生成失败: {e}", exc_info=True)
        return None
