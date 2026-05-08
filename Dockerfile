# gaokao-agent 后端部署
FROM python:3.12-slim

WORKDIR /app

# 安装 curl（用于运行时下载数据库）
RUN apt-get update && apt-get install -y curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 先复制 requirements.txt（利用 Docker 缓存）
COPY backend/requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端应用代码
COPY backend/ .

# 复制数据库文件（避免运行时下载失败）
COPY backend/data/gaokao.db data/gaokao.db

# 复制 start.sh
COPY start.sh .

# 确保 start.sh 可执行
RUN chmod +x start.sh

EXPOSE 10000

# 使用 start.sh 启动（支持运行时下载数据库）
CMD ["bash", "start.sh"]
