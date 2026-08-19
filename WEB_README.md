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

## 数据迁移与容器重建手册

### 数据分布

```
容器内项目目录（代码，来自 git，可随时重建）
  app.py, AGENTS.md ...        ← 代码，git pull 随时更新

持久卷（挂载到容器内 /data，容器删了数据也在）
  auth.json                    ← 登录密码
  workspaces/                  ← 每个任务一个文件夹，多任务并存不覆盖
  opencode-config/             ← opencode 配置/模型选择
  opencode-data/               ← /connect 粘贴的 API key 与模型数据库
  logs/                        ← 服务日志
```

**核心概念：卷 = 数据（不可再生，必须保）+ 代码/依赖/配置 = 可重建（几行命令）。**

### 首次迁移（把容器数据搬进卷）

```bash
# 宿主机：先备份旧容器全部家目录（安全网）
docker exec <旧容器名> tar -C /home -cf - acs > ~/reqdata-backup/home-acs.tar

# 宿主机：重建容器并挂卷（宿主机目录 ~/reqdata 挂到容器 /data）
docker stop <旧容器名> && docker rm <旧容器名>
docker run -itd \
  --name requirement-assistant \
  --restart unless-stopped \
  -v ~/reqdata:/data \
  -p 8080:8080 \
  -p 20000:22 \
  <镜像名> \
  bash

# 宿主机：恢复数据
docker cp ~/reqdata-backup/home-acs.tar requirement-assistant:/tmp/
docker exec requirement-assistant bash -c 'tar -C /home -xf /tmp/home-acs.tar && rm -f /tmp/home-acs.tar'

# 容器内：把该持久化的数据搬进卷（登录后执行）
cd /home/acs/opt/Requirement-Analysis-Assistant
mv auth.json /data/auth.json
mv workspaces /data/workspaces 2>/dev/null
mkdir -p /data/opencode-config /data/opencode-data
mv ~/.config/opencode /data/opencode-config/opencode
mv ~/.local/share/opencode /data/opencode-data/opencode

# 容器内：配置环境变量并启动
cat >> ~/.bashrc <<'EOF'
export DATA_DIR=/data
export XDG_CONFIG_HOME=/data/opencode-config
export XDG_DATA_HOME=/data/opencode-data
EOF
source ~/.bashrc
./start.sh
```

### 日常重建容器（以后迁移只需 4 步）

数据已在卷里，不需要再备份/恢复家目录，只需重建容器后装程序：

```bash
# 宿主机：重建容器（挂同一个卷，端口照旧）
docker run -itd \
  --name requirement-assistant \
  --restart unless-stopped \
  -v ~/reqdata:/data \
  -p 8080:8080 \
  -p 20000:22 \
  <镜像名> \
  bash

# 容器内：装代码 + 依赖 + 配置（4 步）
git clone <仓库地址> /home/acs/opt/Requirement-Analysis-Assistant
cd /home/acs/opt/Requirement-Analysis-Assistant
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env    # 修改 DATA_DIR=/data 等
./start.sh              # 卷已挂好，数据自动读回
```

### 注意事项

- 宿主机挂载目录（如 `~/reqdata`）务必放在系统盘之外或定期备份；要迁移数据时直接整体复制该目录即可
- opencode 二进制（`~/.opencode/bin/opencode`）和 venv 不在卷里，重建容器后需重装（`npm i -g opencode-ai@1.18.18` 或你习惯的安装方式）
- 首次启动后若 opencode 无模型，执行 `opencode` 后 `/connect` 粘贴 key 并选择模型，凭据写入 `$XDG_DATA_HOME/opencode/auth.json`（卷内，会持久化）
