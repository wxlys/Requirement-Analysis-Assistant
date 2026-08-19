#!/usr/bin/env bash
set -e

# 启动 OpenCode Server（仅监听容器内 127.0.0.1，不对外暴露）
# opencode 的模型/provider 配置通过 ~/.config/opencode/opencode.json 或环境变量注入
opencode serve --hostname 127.0.0.1 --port 4096 &

# 启动 Flask Web 服务
exec python app.py
