import json
import os
import platform
from datetime import datetime
from typing import Any

from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from src.utils.logging.logger import get_logger

logger = get_logger(__name__)

_pre_text = (
    "本项目使用{}+LLM{}进行音频文本提取和润色，"
    "ASR模型提取的文本可能存在错误和不准确之处，"
    "以及润色之后的文本可能会与原意有所偏差，请仔细辨别。"
)


def get_system_font_paths() -> list[str]:
    """
    根据操作系统获取字体搜索路径
    :return: 字体路径列表
    """
    system = platform.system()
    paths = []

    if system == "Windows":
        paths = [
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
        ]
    elif system == "Darwin":  # macOS
        paths = [
            "/System/Library/Fonts",
            "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ]
    else:  # Linux 和其他Unix系统
        paths = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/.local/share/fonts"),
        ]

    # 过滤掉不存在的路径
    return [p for p in paths if os.path.exists(p)]


def find_chinese_font() -> str | None:
    """
    跨平台查找可用的中文字体
    :return: 找到的字体文件路径，如果未找到则返回 None
    """
    # 1. 优先使用环境变量指定的字体
    env_font = os.environ.get("CHINESE_FONT_PATH")
    if env_font and os.path.isfile(env_font):
        logger.info(f"使用环境变量指定的字体: {env_font}")
        return env_font

    # 2. 定义不同操作系统的字体候选列表
    system = platform.system()

    if system == "Windows":
        font_candidates = [
            "simfang.ttf",  # 仿宋
            "simsun.ttc",  # 宋体
            "simhei.ttf",  # 黑体
            "msyh.ttc",  # 微软雅黑
            "msyhbd.ttc",  # 微软雅黑粗体
            "simkai.ttf",  # 楷体
        ]
    elif system == "Darwin":  # macOS
        font_candidates = [
            "PingFang.ttc",
            "STHeiti Light.ttc",
            "STHeiti Medium.ttc",
            "STSong.ttf",
            "STFangsong.ttf",
            "Songti.ttc",
            "STKaiti.ttf",
        ]
    else:  # Linux
        font_candidates = [
            # Noto Sans CJK
            "NotoSansCJK-Regular.ttc",
            "NotoSerifCJK-Regular.ttc",
            "NotoSansCJK.ttc",
            "NotoSerifCJK.ttc",
            # WenQuanYi
            "wqy-microhei.ttc",
            "wqy-zenhei.ttc",
            # Source Han Sans/Serif
            "SourceHanSansCN-Regular.otf",
            "SourceHanSerifCN-Regular.otf",
            # Droid Sans Fallback
            "DroidSansFallbackFull.ttf",
            "DroidSansFallback.ttf",
            # AR PL fonts
            "uming.ttc",
            "ukai.ttc",
        ]

    # 3. 搜索字体
    font_paths = get_system_font_paths()

    for font_dir in font_paths:
        for font_name in font_candidates:
            # 直接匹配
            font_path = os.path.join(font_dir, font_name)
            if os.path.isfile(font_path):
                logger.info(f"找到中文字体: {font_path}")
                return font_path

            # 递归搜索（限制深度为2，避免性能问题）
            for root, dirs, files in os.walk(font_dir):
                # 限制搜索深度
                depth = root[len(font_dir) :].count(os.sep)
                if depth >= 2:
                    dirs.clear()
                    continue

                if font_name in files:
                    font_path = os.path.join(root, font_name)
                    logger.info(f"找到中文字体: {font_path}")
                    return font_path

    logger.warning("未找到中文字体，将使用默认字体（可能无法正确显示中文）")
    return None


def get_font_path() -> str:
    """
    获取字体路径，如果找不到则抛出异常
    :return: 字体文件路径
    """
    font_path = find_chinese_font()
    if font_path is None:
        error_msg = (
            "未找到可用的中文字体。请安装中文字体包或通过环境变量 CHINESE_FONT_PATH 指定字体路径。\n"
            "Linux 用户可以安装以下字体包之一:\n"
            "  - Arch Linux: sudo pacman -S noto-fonts-cjk 或 wqy-microhei\n"
            "  - Debian/Ubuntu: sudo apt install fonts-noto-cjk 或 fonts-wqy-microhei\n"
            "  - Fedora/RHEL: sudo dnf install google-noto-sans-cjk-fonts 或 wqy-microhei-fonts\n"
            "或者通过环境变量指定: export CHINESE_FONT_PATH=/path/to/your/font.ttf"
        )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    return font_path


# 初始化字体（延迟加载，不阻止应用启动）
_font_initialized = False
_font_error = None


def _ensure_font_loaded():
    """
    确保字体已加载，如果失败则抛出异常
    """
    global _font_initialized, _font_error

    if _font_initialized:
        return  # 已加载成功

    if _font_error is not None:
        raise _font_error  # 之前加载失败

    # 尝试加载字体
    try:
        font_ttf_path = get_font_path()
        pdfmetrics.registerFont(TTFont("ChineseFont", font_ttf_path))
        addMapping("ChineseFont", 0, 0, "ChineseFont")  # 正常字体
        logger.info(f"成功加载字体: {font_ttf_path}")
        _font_initialized = True
    except Exception as e:
        logger.error(f"字体加载失败: {e}")
        _font_error = e
        raise


def text_to_pdf(
    txt: str,
    with_img: bool,
    title: str,
    output_dir: str,
    ASR_model: str,
    LLM_info: str = "",
) -> str:
    """
    将文本转换为 PDF，并将每页转换为图片
    """
    # 延迟加载字体（仅在实际需要生成 PDF 时）
    _ensure_font_loaded()

    # TODO: 修复pdf中英文混合的排版问题
    os.makedirs(output_dir, exist_ok=True)

    # PDF 保存路径
    pdf_path = os.path.join(output_dir, "output.pdf")

    # 文档配置
    font_size = 14
    leading = font_size * 1.2  # 1.2倍行距
    margin_x = 10 * mm
    margin_y = 10 * mm

    # 样式定义
    normal_style = ParagraphStyle(
        name="Normal",
        fontName="ChineseFont",
        fontSize=font_size,
        leading=leading,
        firstLineIndent=18,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
    )

    pre_style = ParagraphStyle(
        name="PreText",
        fontName="ChineseFont",
        fontSize=font_size - 1,
        leading=font_size * 1.1,
        textColor=colors.gray,
        spaceAfter=12,
        alignment=TA_JUSTIFY,
    )

    title_style = ParagraphStyle(
        name="Title",
        fontName="ChineseFont",
        fontSize=font_size + 4,
        leading=font_size + 6,
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    # 构造内容
    story = []

    if title:
        story.append(Paragraph(title.strip(), title_style))

    pre_text = _pre_text.format(ASR_model, LLM_info)
    story.append(Paragraph(pre_text, pre_style))

    # 正文处理
    paragraphs = [
        Paragraph(line.strip(), normal_style) for line in txt.strip().split("\n") if line.strip()
    ]
    story.extend(paragraphs)

    # 构建 PDF
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=margin_x,
        rightMargin=margin_x,
        topMargin=margin_y,
        bottomMargin=margin_y,
    )

    doc.build(story)
    logger.info(f"PDF 已保存到：{pdf_path}")

    if not with_img:
        return pdf_path

    img_dir = os.path.join(output_dir, "output_img")
    os.makedirs(img_dir, exist_ok=True)

    # PDF 转为图片
    images = convert_from_path(pdf_path, dpi=300)
    image_paths = []

    for i, img in enumerate(images):
        img_path = os.path.join(img_dir, f"page_{i + 1}.png")
        img.save(img_path)
        image_paths.append(img_path)

    logger.info(f"共导出 {len(image_paths)} 张图片到：{img_dir}")
    for img_path in image_paths:
        logger.info(f"图片路径：{img_path}")

    return pdf_path


def get_display_width(txt: str) -> int:
    """
    计算一行文本的显示宽度，中文宽度记为2，英文为1
    :param txt: 文本内容
    :return: 显示宽度
    """
    width = 0
    for ch in txt:
        if "\u4e00" <= ch <= "\u9fff" or ch in "，。！、？：“”‘’（）《》【】":
            width += 2
        else:
            width += 1
    return width


def wrap_text_by_display_width(txt: str, max_width: int) -> list:
    """
    按照显示宽度进行换行
    :param txt: 文本内容
    :param max_width: 最大显示宽度
    :return: 换行后的文本列表
    """
    lines = []
    line = ""
    line_width = 0
    for ch in txt:
        ch_width = 2 if "\u4e00" <= ch <= "\u9fff" or ch in "，。！？：“”‘’（）《》【】" else 1
        if line_width + ch_width > max_width:
            lines.append(line)
            line = ch
            line_width = ch_width
        else:
            line += ch
            line_width += ch_width
    if line:
        lines.append(line)
    return lines


def text_to_one_image(txt: str, output_path: str, title: str | None = None) -> str:
    """
    将文本转换为单张图片
    :param txt: 文本内容
    :param output_path: 输出路径
    :param title: 文本标题（可选）
    :return: 输出文件路径
    """
    # 延迟加载字体（仅在实际需要生成图片时）
    _ensure_font_loaded()

    pre_text = _pre_text.format("")
    if title is None:
        txt = pre_text + txt
    else:
        txt = title + "\n\n" + pre_text + txt

    font_path = get_font_path()  # 使用函数获取字体路径而不是全局变量
    font_size = 28
    line_spacing = 12
    paragraph_spacing = 30
    indent_spaces = "　　"
    max_display_width = 56  # 每行最大显示宽度：28个中文或等效宽度

    paragraphs = [indent_spaces + line.strip() for line in txt.strip().split("\n") if line.strip()]
    font = ImageFont.truetype(font_path, font_size)
    lines = []

    for para in paragraphs:
        wrapped_lines = wrap_text_by_display_width(para, max_display_width)
        lines.extend(wrapped_lines)
        lines.append("")

    image_height = (font_size + line_spacing) * len(lines) + paragraph_spacing
    max_width = 1000
    image = Image.new("RGB", (max_width, image_height + 100), color="white")
    draw = ImageDraw.Draw(image)

    y = 50
    for line in lines:
        if line.strip() == "":
            y += paragraph_spacing
        else:
            draw.text((60, y), line, font=font, fill="black")
            y += font_size + line_spacing

    os.makedirs(output_path, exist_ok=True)
    filename = "output.png"
    output_file_path = os.path.join(output_path, filename)
    image.save(output_file_path)
    logger.info(f"文本已保存为图片：{output_file_path}")

    return output_file_path


def text_to_img_or_pdf(
    txt: str,
    output_style: str,
    output_path: str,
    ASR_model: str,
    title: str | None = None,
    LLM_info: str = "",
    metadata: dict[str, Any] | None = None,
    summary_text: str | None = None,
) -> str:
    """
    将文本转换为图片或PDF/Markdown/JSON
    :param txt: 文本内容
    :param output_style: 输出样式（'pdf_with_img', 'pdf_only', 'img_only', 'markdown', 'json', 'text_only'）
    :param title: 文本标题（可选）
    :param output_path: 输出路径
    :param LLM_info: LLM信息（可选）
    :param metadata: 元信息（JSON/Markdown 使用）
    :param summary_text: 摘要文本（JSON/Markdown 可选）
    :return: 输出文件路径
    """
    if metadata is None:
        metadata = {
            "asr_model": ASR_model,
            "llm_info": LLM_info,
        }

    if output_style == "pdf_with_img":
        return text_to_pdf(
            txt,
            with_img=True,
            title=title,
            output_dir=output_path,
            LLM_info=LLM_info,
            ASR_model=ASR_model,
        )
    if output_style == "pdf_only":
        return text_to_pdf(
            txt,
            with_img=False,
            title=title,
            output_dir=output_path,
            LLM_info=LLM_info,
            ASR_model=ASR_model,
        )
    if output_style == "img_only":
        return text_to_one_image(txt, output_path=output_path, title=title)
    if output_style == "markdown":
        return text_to_markdown(
            txt,
            output_path=output_path,
            title=title,
            metadata=metadata,
            summary_text=summary_text,
        )
    if output_style in ("json", "text_only"):
        return text_to_json(
            txt,
            output_path=output_path,
            title=title,
            metadata=metadata,
            summary_text=summary_text,
        )
    raise ValueError(f"Unsupported output style: {output_style}")


def text_to_markdown(
    txt: str,
    output_path: str,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
    summary_text: str | None = None,
) -> str:
    """
    将文本转换为 Markdown
    :param txt: 文本内容
    :param output_path: 输出路径
    :param title: 文本标题（可选）
    :param metadata: 元信息（可选）
    :param summary_text: 摘要文本（可选）
    :return: 输出文件路径
    """
    os.makedirs(output_path, exist_ok=True)
    output_file_path = os.path.join(output_path, "output.md")

    lines = []
    if title:
        lines.append(f"# {title.strip()}")
        lines.append("")

    if metadata:
        lines.append("## 元信息")
        lines.append("")
        for key, value in metadata.items():
            label = key
            if key == "asr_model":
                label = "ASR模型"
            elif key == "llm_info":
                label = "LLM信息"
            lines.append(f"- {label}: {value}")
        lines.append("")

    if summary_text:
        lines.append("## 摘要")
        lines.append("")
        lines.append(summary_text.strip())
        lines.append("")

    lines.append("## 正文")
    lines.append("")
    lines.append(txt.strip())
    lines.append("")

    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Markdown 已保存到：{output_file_path}")
    return output_file_path


def text_to_json(
    txt: str,
    output_path: str,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
    summary_text: str | None = None,
) -> str:
    """
    将文本转换为 JSON
    :param txt: 文本内容
    :param output_path: 输出路径
    :param title: 文本标题（可选）
    :param metadata: 元信息（可选）
    :param summary_text: 摘要文本（可选）
    :return: 输出文件路径
    """
    os.makedirs(output_path, exist_ok=True)
    output_file_path = os.path.join(output_path, "output.json")

    output_data = {
        "title": title,
        "text": txt,
        "summary": summary_text,
        "meta": metadata or {},
        "exported_at": datetime.now().isoformat(),
    }

    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"JSON 已保存到：{output_file_path}")
    return output_file_path
