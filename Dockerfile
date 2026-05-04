# Hermes Gateway - 高报专家部署
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY server.py .
COPY SOUL.md .

EXPOSE 10000

# 启动命令
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 server:app
