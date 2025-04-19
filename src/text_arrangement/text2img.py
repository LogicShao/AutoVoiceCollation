import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

from ..config import OUTPUT_DIR


def text_to_image(txt: str, output_path: str = OUTPUT_DIR) -> str:
    """
    将文本转换为图片，支持中文和英文，使用仿宋字体。
    :param txt: 要转换的文本
    :param output_path: 输出图片的路径
    :return: 输出图片的路径
    """
    # 参数设置
    font_path = "../../ttf/simfang.ttf"  # 使用仿宋字体
    font_size = 28
    line_spacing = 12  # 行间距
    paragraph_spacing = 30  # 段间距
    indent_spaces = '　　'  # 中文全角空格实现首行缩进

    # 文本处理：段落分割 + 首行缩进
    paragraphs = [indent_spaces + line.strip() for line in txt.strip().split('\n') if line.strip()]

    # 加载字体
    font = ImageFont.truetype(font_path, font_size)

    # 准备画布大小预估（后面动态生成）
    max_width = 1000
    lines = []

    for para in paragraphs:
        wrapped = textwrap.wrap(para, width=28)  # 控制每行字数，视字体大小调整
        lines.extend(wrapped)
        lines.append('')  # 空行作为段间距

    # 图像尺寸
    image_height = (font_size + line_spacing) * len(lines) + paragraph_spacing
    image = Image.new("RGB", (max_width, image_height + 100), color="white")
    draw = ImageDraw.Draw(image)

    # 绘制文本
    y = 50  # 顶部边距
    for line in lines:
        if line.strip() == "":
            y += paragraph_spacing
        else:
            draw.text((60, y), line, font=font, fill="black")  # 左边距
            y += font_size + line_spacing

    # 创建输出目录
    os.makedirs(output_path, exist_ok=True)
    filename = 'output.png'
    output_file_path = os.path.join(output_path, filename)
    image.save(output_file_path)
    print(f"文本已保存为图片：{output_file_path}")

    return output_file_path


if __name__ == "__main__":
    with open("../../out/polish_text.txt", "r", encoding="utf-8") as f:
        text = f.read()
    text_to_image(text)
