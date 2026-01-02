@echo off
REM ================================
REM AutoVoiceCollation Docker 快速启动脚本 (Windows)
REM ================================

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM 颜色定义（Windows 10+ 支持）
set "RED=[31m"
set "GREEN=[32m"
set "YELLOW=[33m"
set "BLUE=[34m"
set "NC=[0m"

REM 检查 Docker 是否安装
echo [INFO] 检查依赖...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker 未安装！请先安装 Docker Desktop。
    echo [INFO] 下载地址: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose 未安装或版本过低！
    pause
    exit /b 1
)

echo [SUCCESS] 依赖检查通过！

REM 检查 .env 文件
echo [INFO] 检查配置文件...
if not exist .env (
    if exist .env.example (
        echo [WARNING] .env 文件不存在，正在从 .env.example 复制...
        copy .env.example .env
        echo [SUCCESS] .env 文件已创建！
        echo [WARNING] 请编辑 .env 文件，配置你的 API Keys
        echo.
        pause
    ) else (
        echo [ERROR] .env.example 文件不存在！
        pause
        exit /b 1
    )
) else (
    echo [SUCCESS] 配置文件检查完成！
)

REM Create necessary directories
echo [INFO] Creating necessary directories...
if not exist out mkdir out
if not exist download mkdir download
if not exist temp mkdir temp
if not exist logs mkdir logs
if not exist models mkdir models
echo [SUCCESS] Directories created!

REM 处理命令参数
set "command=%~1"
if "%command%"=="" set "command=start"

if "%command%"=="start" goto :start
if "%command%"=="start-cpu" goto :start_cpu
if "%command%"=="stop" goto :stop
if "%command%"=="restart" goto :restart
if "%command%"=="logs" goto :logs
if "%command%"=="build" goto :build
if "%command%"=="clean" goto :clean
if "%command%"=="help" goto :help

echo [ERROR] 未知命令: %command%
goto :help

:start
echo [INFO] 启动服务（GPU 模式）...
echo [INFO] 如果没有 GPU，请使用: docker-start.bat start-cpu
docker compose build
docker compose up -d
if errorlevel 1 (
    echo [ERROR] 启动失败！尝试使用 CPU 模式: docker-start.bat start-cpu
    pause
    exit /b 1
)
echo [SUCCESS] 服务已启动！
echo [INFO] 访问地址: http://localhost:8000
echo [INFO] 查看日志: docker compose logs -f
echo [INFO] 停止服务: docker compose down
pause
exit /b 0

:start_cpu
echo [INFO] 启动服务（CPU 模式）...
docker compose build autovoicecollation-api-cpu
docker compose --profile cpu-only up -d
if errorlevel 1 (
    echo [ERROR] 启动失败！
    pause
    exit /b 1
)
echo [SUCCESS] 服务已启动！
echo [INFO] 访问地址: http://localhost:8001
echo [INFO] 查看日志: docker compose logs -f
echo [INFO] 停止服务: docker compose down
pause
exit /b 0

:stop
echo [INFO] 停止服务...
docker compose down
echo [SUCCESS] 服务已停止！
pause
exit /b 0

:restart
echo [INFO] 重启服务...
docker compose restart
echo [SUCCESS] 服务已重启！
pause
exit /b 0

:logs
docker compose logs -f
exit /b 0

:build
echo [INFO] 重新构建镜像...
docker compose build --no-cache
echo [SUCCESS] 镜像重新构建完成！
pause
exit /b 0

:clean
echo [WARNING] 这将删除所有相关的容器和镜像！
set /p confirm="确定要继续吗？(yes/no): "
if /i "%confirm%"=="yes" (
    echo [INFO] 清理容器和镜像...
    docker compose down --rmi all --volumes
    echo [SUCCESS] 清理完成！
) else (
    echo [INFO] 操作已取消。
)
pause
exit /b 0

:help
echo AutoVoiceCollation Docker 快速启动脚本 (Windows)
echo.
echo 用法: docker-start.bat [选项]
echo.
echo 选项:
echo     start           启动服务（GPU 模式）
echo     start-cpu       使用 CPU 模式启动
echo     stop            停止服务
echo     restart         重启服务
echo     logs            查看日志
echo     build           重新构建镜像
echo     clean           清理所有容器和镜像
echo     help            显示此帮助信息
echo.
echo 示例:
echo     docker-start.bat start        # 启动 GPU 模式
echo     docker-start.bat start-cpu    # 启动 CPU 模式
echo     docker-start.bat logs         # 查看实时日志
echo     docker-start.bat stop         # 停止服务
echo.
pause
exit /b 0
