@echo off
chcp 65001 >nul
title 超星签到助手 - 一键启动
cd /d "%~dp0"
echo ========================================
echo   🚀 超星签到助手 - 一键启动 & 公网隧道
echo ========================================

:: 1. 检查并自动下载 cloudflared
if not exist "cloudflared.exe" (
    echo [⏳] 正在下载内网穿透工具...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe'"
    if exist "cloudflared.exe" (echo [✅] 工具下载完成！) else (echo [❌] 下载失败，请检查网络)
    echo.
)

:: 2. 启动本地服务（必须输入正确校验码才会运行）
echo [🟢] 正在启动主程序，请输入校验码...
start /WAIT "超星本地服务" python main.py

:: 3. 强制检测8000端口（修复核心BUG：逻辑彻底修正）
echo [⏳] 等待服务启动中...
:CHECK_PORT
powershell -NoProfile -Command "if ((Test-NetConnection 127.0.0.1 -Port 8000).TcpTestSucceeded) {exit 0} else {exit 1}"
if %errorlevel% equ 0 (
    goto START_TUNNEL
)
timeout /t 1 /nobreak >nul
goto CHECK_PORT

:: 4. 启动公网隧道 + 自动打开链接（无卡顿、无临时文件）
:START_TUNNEL
echo.
echo [✅] 服务启动成功！正在生成公网链接...
echo [📲] 公网链接将自动弹出浏览器
echo ========================================
echo.

:: 启动穿透并自动打开链接（稳定版）
start /b cloudflared tunnel --url http://127.0.0.1:8000
timeout /t 3 /nobreak >nul
start https://localhost:8000

:: 5. 保持窗口运行，防止程序退出
echo.
echo [✅] 服务已全程运行，请勿关闭此窗口
echo ========================================
pause >nul

:: 6. 退出时清理服务
taskkill /fi "WINDOWTITLE eq 超星本地服务" /f >nul 2>&1
taskkill /f /im cloudflared.exe >nul 2>&1