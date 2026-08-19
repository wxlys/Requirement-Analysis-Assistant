#!/usr/bin/env bash
# 启动需求分析服务（OpenCode Server + Flask Web）
# 适用环境：容器/主机内直接运行（当前服务器即容器，服务直接在容器内跑，无需再套 Docker）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# 优先加载项目根目录的 .env（若存在），否则使用默认值
if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

# 数据目录：默认项目根目录；容器部署时请在 .env 中设为持久卷路径，例如 DATA_DIR=/data
export DATA_DIR="${DATA_DIR:-$ROOT}"
export OPENCODE_URL="${OPENCODE_URL:-http://127.0.0.1:4096}"
export WEB_HOST="${WEB_HOST:-0.0.0.0}"
export WEB_PORT="${WEB_PORT:-8080}"
# opencode 凭据/模型存储位置（/connect 粘贴的 key 存在 $XDG_DATA_HOME/opencode/auth.json）
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

mkdir -p "$DATA_DIR/workspaces" "$DATA_DIR/logs"
mkdir -p "$XDG_DATA_HOME/opencode"

PYTHON="$ROOT/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON=python3

echo "DATA_DIR=$DATA_DIR"
echo "XDG_DATA_HOME=$XDG_DATA_HOME"
echo "OPENCODE_URL=$OPENCODE_URL"

# OpenCode Server（仅监听 127.0.0.1，不对外暴露）
nohup opencode serve --hostname 127.0.0.1 --port 4096 >"$DATA_DIR/logs/opencode.log" 2>&1 &
echo $! > "$DATA_DIR/logs/opencode.pid"

# Flask Web 服务
nohup "$PYTHON" app.py >"$DATA_DIR/logs/web.log" 2>&1 &
echo $! > "$DATA_DIR/logs/web.pid"

echo "已启动 opencode(pid $(cat "$DATA_DIR/logs/opencode.pid")) web(pid $(cat "$DATA_DIR/logs/web.pid"))"
echo "日志目录：$DATA_DIR/logs/"
echo "Web: http://$WEB_HOST:$WEB_PORT"