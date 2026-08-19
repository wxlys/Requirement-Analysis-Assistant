# 需求分析助手 单容器镜像：OpenCode Server + Flask Web
# 构建阶段：安装 opencode CLI（模型 provider 配置请按你的环境注入，见下）
FROM node:20-slim AS opencode-stage
RUN npm install -g opencode-ai@1.18.18

# 运行阶段
FROM python:3.11-slim

WORKDIR /app

# 从构建阶段复制 opencode CLI 及依赖
COPY --from=opencode-stage /usr/local/bin/opencode /usr/local/bin/opencode
COPY --from=opencode-stage /usr/local/lib/node_modules /usr/local/lib/node_modules

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 项目代码（.dockerignore 已排除运行时产物）
COPY . .

RUN chmod +x entrypoint.sh

ENV WEB_HOST=0.0.0.0
ENV WEB_PORT=8080
ENV OPENCODE_URL=http://127.0.0.1:4096
ENV DATA_DIR=/data

EXPOSE 8080 4096

CMD ["bash", "entrypoint.sh"]
