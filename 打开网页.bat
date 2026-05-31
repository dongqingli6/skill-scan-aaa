@echo off
chcp 65001 >nul
title SkillSentinel - Skill 安全研判平台
cd /d "%~dp0"

echo ============================================================
echo   SkillSentinel - Skill 安全研判平台   一键启动
echo ============================================================
echo.

REM ---------- 1. 检测 Python ----------
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
  where py >nul 2>nul && set "PY=py"
)
if not defined PY (
  echo [错误] 未在系统中检测到 Python。
  echo.
  echo 请先安装 Python 3.10 或以上版本：
  echo     https://www.python.org/downloads/
  echo 安装时请务必勾选 "Add Python to PATH"。
  echo 安装完成后重新双击本文件即可。
  echo.
  pause
  exit /b 1
)

echo [1/3] 已检测到 Python，准备安装依赖...
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo [警告] 依赖安装失败，可能是网络问题。
  echo 你可以手动运行下面这条命令排查：
  echo     %PY% -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

echo [2/3] 依赖准备完毕，正在启动 Web 服务（监听 http://127.0.0.1:8765/）...
echo       浏览器将在 3 秒后自动打开。
echo       关闭本窗口或按 Ctrl + C 可停止服务。
echo.

REM ---------- 2. 3 秒后自动打开浏览器 ----------
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8765/"

echo [3/3] 服务运行日志：
echo ------------------------------------------------------------
%PY% web_ui\app.py
