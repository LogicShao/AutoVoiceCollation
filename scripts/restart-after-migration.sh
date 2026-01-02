#!/bin/bash
# 重启脚本 - 修复配置迁移后的问题

echo "==================================="
echo "清理并重启 API 服务器"
echo "==================================="

# 1. 清理 Python 缓存
echo -e "\n[1/4] 清理 Python 字节码缓存..."
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo "✓ 缓存已清理"

# 2. 验证配置系统
echo -e "\n[2/4] 验证新配置系统..."
python -c "from src.utils.config import get_config; c = get_config(); print(f'✓ 配置系统正常: {c.paths.download_dir}')" || {
    echo "✗ 配置系统验证失败！"
    exit 1
}

# 3. 检查是否有 API 服务器正在运行
echo -e "\n[3/4] 检查运行中的服务..."
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "检测到端口 8000 上有进程，尝试停止..."
    kill $(lsof -ti:8000) 2>/dev/null || echo "无法自动停止，请手动停止后重试"
    sleep 2
fi

# 4. 提示重启
echo -e "\n[4/4] 准备重启..."
echo "==================================="
echo "请执行以下命令启动 API 服务器："
echo "  python api.py"
echo ""
echo "==================================="
