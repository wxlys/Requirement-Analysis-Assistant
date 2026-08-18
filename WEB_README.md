# Web 服务部署

## 本地启动

先确保 OpenCode Server 已在项目根目录运行：

```bash
opencode serve --hostname 127.0.0.1 --port 4096
```

另开终端安装依赖并启动 Web 服务：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

浏览器访问 `http://127.0.0.1:8080`。

如果 Web 服务和 OpenCode Server 不在同一台机器，可设置：

```bash
export OPENCODE_URL=http://127.0.0.1:4096
export WEB_HOST=127.0.0.1
export WEB_PORT=8080
```

## 生产运行

建议使用 systemd 管理 Web 服务，并让 Nginx 负责 HTTPS 和公网访问。OpenCode Server 不应直接暴露到公网。

```ini
[Unit]
Description=Requirement Analysis Web
After=network.target

[Service]
User=wsr
WorkingDirectory=/opt/requirement-assistant/Requirement-Analysis-Assistant
Environment=OPENCODE_URL=http://127.0.0.1:4096
Environment=WEB_HOST=127.0.0.1
Environment=WEB_PORT=8080
ExecStart=/opt/requirement-assistant/Requirement-Analysis-Assistant/.venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

保存为 `/etc/systemd/system/requirement-assistant-web.service` 后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now requirement-assistant-web
sudo systemctl status requirement-assistant-web
```

当前 MVP 使用项目目录中的共享输出文件，适合先验证流程。正式部署多用户并发前，需要将每个任务隔离到独立工作区，并为 Web 服务增加登录、文件大小限制和任务权限控制。
