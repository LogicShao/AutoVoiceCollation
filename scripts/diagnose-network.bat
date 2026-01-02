@echo off
REM Windows Docker 网络诊断和修复脚本

echo ===================================
echo Docker 网络诊断工具
echo ===================================
echo.

echo 1. 检查容器状态...
docker ps | findstr avc
echo.

echo 2. 检查端口绑定...
docker inspect avc-api --format="{{json .HostConfig.PortBindings}}"
echo.

echo 3. 从容器内部测试...
docker exec avc-api curl -s http://localhost:8000/health | findstr "healthy"
if errorlevel 1 (
    echo [ERROR] 容器内部无法访问服务
) else (
    echo [OK] 容器内部可以访问服务
)
echo.

echo 4. 从主机测试 localhost...
curl -s --connect-timeout 3 http://localhost:8000/health | findstr "healthy" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] localhost:8000 无法访问
) else (
    echo [OK] localhost:8000 可以访问
)
echo.

echo 5. 从主机测试 127.0.0.1...
curl -s --connect-timeout 3 http://127.0.0.1:8000/health | findstr "healthy" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 127.0.0.1:8000 无法访问
) else (
    echo [OK] 127.0.0.1:8000 可以访问
)
echo.

echo 6. 检查防火墙规则...
netsh advfirewall firewall show rule name=all | findstr "8000" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 未找到端口 8000 的防火墙规则
) else (
    echo [INFO] 找到端口 8000 的防火墙规则
)
echo.

echo ===================================
echo 诊断完成
echo ===================================
echo.

echo 推荐解决方案:
echo 1. 重启 Docker Desktop (Settings ^> Restart)
echo 2. 添加防火墙规则:
echo    netsh advfirewall firewall add rule name="Docker Port 8000" dir=in action=allow protocol=TCP localport=8000
echo 3. 检查 Docker Desktop Settings ^> Resources ^> WSL Integration
echo 4. 尝试使用不同的端口 (修改 docker-compose.yml)
echo.
pause
