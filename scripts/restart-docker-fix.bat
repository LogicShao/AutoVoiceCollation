@echo off
REM Quick fix script for Docker network issue
echo ===================================
echo Docker Network Fix - Restart Containers
echo ===================================
echo.

echo Step 1: Stopping containers...
docker compose down
echo.

echo Step 2: Waiting for cleanup...
timeout /t 3 >nul
echo.

echo Step 3: Starting containers...
docker compose up -d
echo.

echo Step 4: Waiting for service to start...
timeout /t 10 >nul
echo.

echo Step 5: Testing connection...
curl -s --connect-timeout 5 http://localhost:7860 | findstr "Gradio" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Still cannot access localhost:7860
    echo.
    echo Please try Solution 2: Add Firewall Rule
    echo Run this command as Administrator:
    echo netsh advfirewall firewall add rule name="Docker Port 7860" dir=in action=allow protocol=TCP localport=7860
) else (
    echo [SUCCESS] Service is now accessible!
    echo.
    echo Open your browser and visit:
    echo http://localhost:7860
)

echo.
pause
