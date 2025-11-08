@echo off
REM Add Windows Firewall rule for Docker port 7860
REM Must run as Administrator

echo ===================================
echo Add Firewall Rule for Docker Port
echo ===================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This script must run as Administrator!
    echo.
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

echo Adding firewall rule for port 7860...
netsh advfirewall firewall add rule name="Docker Port 7860" dir=in action=allow protocol=TCP localport=7860

if errorlevel 1 (
    echo [ERROR] Failed to add firewall rule
    pause
    exit /b 1
)

echo [SUCCESS] Firewall rule added successfully!
echo.

echo Restarting containers...
docker compose -f "%~dp0docker-compose.yml" restart

echo.
echo Waiting for service to start...
timeout /t 15 >nul

echo.
echo Testing connection...
curl -s --connect-timeout 5 http://localhost:7860 | findstr "Gradio" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Cannot connect yet. Please wait a moment and try:
    echo http://localhost:7860
) else (
    echo [SUCCESS] Service is now accessible!
    echo http://localhost:7860
)

echo.
pause
