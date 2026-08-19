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

浏览器访问 `http://127.0.0.1:8080`，输入登录账号后使用。

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
Environment=DATA_DIR=/opt/requirement-assistant/data
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

`DATA_DIR` 指向持久化目录，存放 `auth.json` 与 `workspaces/`（任务工作区），请确保该目录在系统盘之外或已做好备份。

## 容器内直接部署（当前服务器实际方式）

当前服务器是一个 Docker 容器，服务直接在容器内运行，**不需要再套一层 Docker**。仓库提供 `start.sh` / `stop.sh` 脚本：

```bash
cd /home/acs/opt/Requirement-Analysis-Assistant
./start.sh        # 后台启动 opencode serve(4096) + python app.py(8080)
./stop.sh         # 停止
```

日志输出到 `$DATA_DIR/logs/`（`opencode.log`、`web.log`）。

### 持久化（重要）

容器根文件系统是临时层，**容器重建会丢失全部数据**。必须让宿主机把持久卷挂载进容器（例如挂到 `/data`），然后启动前设置：

```bash
export DATA_DIR=/data                                  # auth.json + workspaces/
export XDG_CONFIG_HOME=/data/opencode-config            # opencode 配置/模型选择
export XDG_DATA_HOME=/data/opencode-data               # opencode 凭据（/connect 粘贴的 key）
./start.sh
```

首次启动后，若 opencode 尚未配置模型，请执行 `opencode` 后用 `/connect` 粘贴 key 并选择模型，凭据会写入 `$XDG_DATA_HOME/opencode/auth.json`。

每个任务在独立工作区 `workspaces/{任务ID}/` 中执行，输入、中间产物、输出均按任务隔离，互不影响，支持多用户并发。任务状态（`jobs`）为内存态，服务重启后清空；磁盘上的产物文件仍保留在工作区内。
