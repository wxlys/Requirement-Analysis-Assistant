#!/usr/bin/env bash
# 停止需求分析服务（与 start.sh 配套）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${DATA_DIR:-$ROOT}"

for name in opencode web; do
  pid_file="$DATA_DIR/logs/$name.pid"
  if [ -f "$pid_file" ]; then
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" && echo "已停止 $name (pid $pid)"
    fi
    rm -f "$pid_file"
  fi
done
echo "已全部停止"