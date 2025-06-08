import os

from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph

pre_text = (
    "本项目使用SenseVoice+LLM进行音频文本提取和润色，"
    "AI提取的文本可能存在错误和不准确之处，"
    "以及润色之后的文本可能会与原意有所偏差，请仔细辨别。\n\n"
)
# 设置字体路径
font_ttf_path = './ttf/simfang.ttf'
pdfmetrics.registerFont(TTFont('FangSong', font_ttf_path))
addMapping('FangSong', 0, 0, 'FangSong')  # 正常字体


def text_to_pdf(txt: str, with_img: bool, title: str, output_dir: str) -> str:
    """
    将文本转换为 PDF，并将每页转换为图片
    :param txt: 文本内容
    :param with_img: 是否将 PDF 转为图片
    :param title: 文本标题（可选）
    :param output_dir: 输出目录
    :return: 输出文件路径
    """
    # TODO: 修复pdf中英文混合的排版问题
    os.makedirs(output_dir, exist_ok=True)
    img_dir = os.path.join(output_dir, "output_img")
    os.makedirs(img_dir, exist_ok=True)

    # PDF 保存路径
    pdf_path = os.path.join(output_dir, "output.pdf")

    # 文档配置
    font_size = 14
    leading = font_size * 1.2  # 1.2倍行距
    margin_x = 10 * mm
    margin_y = 10 * mm

    # 样式定义
    normal_style = ParagraphStyle(
        name='Normal',
        fontName='FangSong',
        fontSize=font_size,
        leading=leading,
        firstLineIndent=18,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
    )

    pre_style = ParagraphStyle(
        name='PreText',
        fontName='FangSong',
        fontSize=font_size - 1,
        leading=font_size * 1.1,
        textColor=colors.gray,
        spaceAfter=12,
        alignment=TA_JUSTIFY,
    )

    title_style = ParagraphStyle(
        name='Title',
        fontName='FangSong',
        fontSize=font_size + 4,
        leading=font_size + 6,
        alignment=TA_CENTER,
        spaceAfter=20
    )

    # 构造内容
    story = []

    if title:
        story.append(Paragraph(title.strip(), title_style))

    story.append(Paragraph(pre_text.strip(), pre_style))

    # 正文处理
    paragraphs = [
        Paragraph(line.strip(), normal_style)
        for line in txt.strip().split('\n') if line.strip()
    ]
    story.extend(paragraphs)

    # 构建 PDF
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=margin_x,
        rightMargin=margin_x,
        topMargin=margin_y,
        bottomMargin=margin_y
    )

    doc.build(story)
    print(f"PDF 已保存到：{pdf_path}")

    if not with_img:
        return pdf_path

    # PDF 转为图片
    images = convert_from_path(pdf_path, dpi=300)
    image_paths = []

    for i, img in enumerate(images):
        img_path = os.path.join(img_dir, f"page_{i + 1}.png")
        img.save(img_path)
        image_paths.append(img_path)

    print(f"共导出 {len(image_paths)} 张图片到：{img_dir}")
    for img_path in image_paths:
        print(f"图片路径：{img_path}")

    return pdf_path


def get_display_width(txt: str) -> int:
    """
    计算一行文本的显示宽度，中文宽度记为2，英文为1
    :param txt: 文本内容
    :return: 显示宽度
    """
    width = 0
    for ch in txt:
        if '\u4e00' <= ch <= '\u9fff' or ch in '，。！、？：“”‘’（）《》【】':
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
    line = ''
    line_width = 0
    for ch in txt:
        ch_width = 2 if '\u4e00' <= ch <= '\u9fff' or ch in '，。！？：“”‘’（）《》【】' else 1
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
    if title is None:
        txt = pre_text + txt
    else:
        txt = title + "\n\n" + pre_text + txt

    font_path = font_ttf_path
    font_size = 28
    line_spacing = 12
    paragraph_spacing = 30
    indent_spaces = '　　'
    max_display_width = 56  # 每行最大显示宽度：28个中文或等效宽度

    paragraphs = [indent_spaces + line.strip() for line in txt.strip().split('\n') if line.strip()]
    font = ImageFont.truetype(font_path, font_size)
    lines = []

    for para in paragraphs:
        wrapped_lines = wrap_text_by_display_width(para, max_display_width)
        lines.extend(wrapped_lines)
        lines.append('')

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
    filename = 'output.png'
    output_file_path = os.path.join(output_path, filename)
    image.save(output_file_path)
    print(f"文本已保存为图片：{output_file_path}")

    return output_file_path


def text_to_img_or_pdf(txt: str, output_style: str, output_path: str, title: str | None = None) -> str:
    """
    将文本转换为图片或PDF
    :param txt: 文本内容
    :param output_style: 输出样式（'pdf with img', 'img only', 'text only', 'pdf only'）
    :param title: 文本标题（可选）
    :param output_path: 输出路径
    :return: 输出文件路径
    """
    if output_style == 'pdf with img':
        return text_to_pdf(txt, with_img=True, title=title, output_dir=output_path)
    elif output_style == 'pdf only':
        return text_to_pdf(txt, with_img=False, title=title, output_dir=output_path)
    elif output_style == 'img only':
        return text_to_one_image(txt, output_path=output_path, title=title)
    else:
        raise ValueError(f"Unsupported output style: {output_style}")
