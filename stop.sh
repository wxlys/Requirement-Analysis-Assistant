#!/usr/bin/env bash
# 停止需求分析服务（与 start.sh 配套）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${DATA_DIR:-$ROOT}"

for name in opencode web; do
  pid_file="$DATA_DIR/logs/$name.pid"
  [ -f "$pid_file" ] || continue
  pid=$(cat "$pid_file")
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
done

# 等待进程退出，超时后强杀
for pattern in "opencode serve" "python app.py"; do
  for _ in $(seq 1 10); do
    pgrep -f "$pattern" >/dev/null 2>&1 || break
    sleep 1
  done
  # 仍然存活则强杀（用精确路径避免误杀本脚本自身）
  pkill -9 -f "/home/acs/.opencode/bin/opencode serve" 2>/dev/null || true
  pkill -9 -f "$ROOT/.venv/bin/python app.py" 2>/dev/null || true
done

echo "已全部停止"