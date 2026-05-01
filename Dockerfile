# gaokao-agent 后端部署（简化版，跳过前端构建）
FROM python:3.12-slim

WORKDIR /app

# 安装后端依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端应用代码（包含 data/ 目录）
COPY backend/ .

# 数据目录
RUN mkdir -p /app/data

EXPOSE 10000

# Render 注入 PORT 环境变量
# 使用启动脚本（自动下载数据库）
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/bin/bash", "/app/start.sh"]
