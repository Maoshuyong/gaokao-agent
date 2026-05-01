# gaokao-agent 后端部署
FROM python:3.12-slim

WORKDIR /app

# 安装 curl（用于构建时下载数据库）
RUN apt-get update && apt-get install -y curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 构建时下载数据库（避免运行时延迟）
RUN mkdir -p data && \
    curl -L -o data/gaokao_shanxi_recruit.db \
    http://tecjtbmlo.hn-bkt.clouddn.com/gaokao_shanxi_recruit.db

# 安装后端依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端应用代码
COPY backend/ .

EXPOSE 10000

# 直接启动应用（无需下载数据库）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-10000}"]
