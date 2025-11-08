#!/bin/bash
# 验证 Docker 容器中的字体配置

echo "=== 验证字体配置 ==="
echo ""

# 1. 检查字体文件是否存在
echo "1. 检查字体文件..."
if docker exec avc-webui test -f /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc 2>/dev/null; then
    echo "   ✓ 字体文件存在"
    docker exec avc-webui ls -lh /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
else
    echo "   ✗ 字体文件不存在"
    echo "   正在检查其他可能的位置..."
    docker exec avc-webui find /usr/share/fonts -name "*wqy*" -o -name "*noto*" 2>/dev/null | head -5
fi

echo ""

# 2. 检查环境变量
echo "2. 检查环境变量..."
FONT_PATH=$(docker exec avc-webui printenv CHINESE_FONT_PATH 2>/dev/null)
if [ -n "$FONT_PATH" ]; then
    echo "   ✓ CHINESE_FONT_PATH=$FONT_PATH"
else
    echo "   ✗ CHINESE_FONT_PATH 未设置"
fi

echo ""

# 3. 检查字体缓存
echo "3. 检查字体缓存..."
docker exec avc-webui fc-list :lang=zh | head -3 2>/dev/null || echo "   字体缓存未找到或 fc-list 不可用"

echo ""

# 4. 测试 Python 导入
echo "4. 测试 Python 模块导入..."
docker exec avc-webui python -c "
import os
print(f'CHINESE_FONT_PATH = {os.environ.get(\"CHINESE_FONT_PATH\", \"未设置\")}')
font_path = os.environ.get('CHINESE_FONT_PATH', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc')
if os.path.exists(font_path):
    print(f'✓ 字体文件可访问: {font_path}')
else:
    print(f'✗ 字体文件不可访问: {font_path}')
" 2>/dev/null || echo "   容器未运行或 Python 不可用"

echo ""
echo "=== 验证完成 ==="
