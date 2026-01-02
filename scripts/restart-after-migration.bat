@echo off
REM 重启脚本 - 修复配置迁移后的问题 (Windows)

echo ===================================
echo 清理并重启 API 服务器
echo ===================================

REM 1. 清理 Python 缓存
echo.
echo [1/4] 清理 Python 字节码缓存...
for /r %%i in (*.pyc) do del "%%i" 2>nul
for /d /r %%i in (__pycache__) do rd /s /q "%%i" 2>nul
echo √ 缓存已清理

REM 2. 验证配置系统
echo.
echo [2/4] 验证新配置系统...
python -c "from src.utils.config import get_config; c = get_config(); print(f'√ 配置系统正常: {c.paths.download_dir}')"
if errorlevel 1 (
    echo × 配置系统验证失败！
    pause
    exit /b 1
)

REM 3. 检查端口占用
echo.
echo [3/4] 检查运行中的服务...
netstat -ano | findstr :8000 >nul
if not errorlevel 1 (
    echo 检测到端口 8000 被占用，请手动停止旧进程
    echo 使用任务管理器或运行: taskkill /F /PID [PID]
    pause
)

REM 4. 提示重启
echo.
echo [4/4] 准备重启...
echo ===================================
echo 请执行以下命令启动 API 服务器：
echo   python api.py
echo.
echo ===================================
pause
