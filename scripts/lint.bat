@echo off
REM Ruff 代码质量检查和修复脚本（Windows 版本）
REM 使用方式: scripts\lint.bat [check|fix|format|all]

setlocal enabledelayedexpansion

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=check"

:check_ruff
where ruff >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 错误: 未找到 ruff，请先安装: pip install ruff
    exit /b 1
)

goto :%ACTION% 2>nul || goto :usage

:check
echo ================================
echo 运行 Ruff Lint 检查（仅检查，不修复）
echo ================================
echo.

ruff check . --statistics
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Lint 检查失败
    echo ⚠️  运行 'scripts\lint.bat fix' 可自动修复部分问题
    exit /b 1
) else (
    echo ✅ Lint 检查通过
)

echo.
echo ================================
echo 运行 Ruff 格式检查（仅检查，不格式化）
echo ================================
echo.

ruff format --check .
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 格式检查失败
    echo ⚠️  运行 'scripts\lint.bat format' 可自动格式化代码
    exit /b 1
) else (
    echo ✅ 格式检查通过
)

goto :end

:fix
echo ================================
echo 运行 Ruff Lint 并自动修复
echo ================================
echo.

ruff check --fix .
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  部分问题无法自动修复，请手动处理
) else (
    echo ✅ Lint 检查并修复完成
)

goto :end

:format
echo ================================
echo 运行 Ruff 代码格式化
echo ================================
echo.

ruff format .
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 代码格式化失败
    exit /b 1
) else (
    echo ✅ 代码格式化完成
)

goto :end

:all
echo ================================
echo 完整的代码质量检查和修复
echo ================================
echo.

echo 步骤 1/3: Lint 检查和修复
echo --------------------------------
ruff check --fix .
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  部分 lint 问题需要手动修复
)

echo.
echo 步骤 2/3: 代码格式化
echo --------------------------------
ruff format .

echo.
echo 步骤 3/3: 最终验证
echo --------------------------------
ruff check . && ruff format --check .
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️  仍有部分问题需要手动修复
    exit /b 1
) else (
    echo.
    echo 🎉 所有检查通过！代码质量良好！
)

goto :end

:usage
echo 使用方式: %~nx0 [check^|fix^|format^|all]
echo.
echo   check   - 仅检查，不修复（默认）
echo   fix     - 检查并自动修复 lint 问题
echo   format  - 自动格式化代码
echo   all     - 执行完整的检查、修复和格式化
exit /b 1

:end
endlocal
