#!/bin/bash
# SkillSentinel - macOS 一键启动器
# 首次使用前请在终端执行一次：chmod +x 打开网页.command
# 之后双击即可启动。

cd "$(dirname "$0")"

echo "============================================================"
echo "  SkillSentinel - Skill 安全研判平台   一键启动"
echo "============================================================"
echo ""

# ---------- 1. 检测 Python ----------
PY=""
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
fi

if [ -z "$PY" ]; then
  echo "[错误] 未在系统中检测到 Python。"
  echo ""
  echo "请先安装 Python 3.10 或以上版本，可选方式："
  echo "  1) 从官网下载:  https://www.python.org/downloads/"
  echo "  2) 使用 Homebrew:  brew install python"
  echo ""
  echo "安装完成后重新双击本文件即可。"
  echo ""
  read -p "按回车键关闭窗口..."
  exit 1
fi

echo "[1/3] 已检测到 $PY，准备安装依赖..."
"$PY" -m pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
  echo ""
  echo "[警告] 依赖安装失败，可能是网络问题。"
  echo "你可以手动运行下面这条命令排查："
  echo "    $PY -m pip install -r requirements.txt"
  echo ""
  read -p "按回车键关闭窗口..."
  exit 1
fi

echo "[2/3] 依赖准备完毕，正在启动 Web 服务（监听 http://127.0.0.1:8765/）..."
echo "      浏览器将在 3 秒后自动打开。"
echo "      关闭此窗口或按 Ctrl + C 可停止服务。"
echo ""

# ---------- 2. 3 秒后自动用默认浏览器打开 ----------
( sleep 3 && open "http://127.0.0.1:8765/" ) &

echo "[3/3] 服务运行日志："
echo "------------------------------------------------------------"
"$PY" web_ui/app.py
