#!/bin/bash
# Render 部署脚本：启动时下载数据库文件
# 数据库从 GitHub Release 下载（v1.0-db）

set -e  # 任何错误都退出

echo "🚀 启动 gaokao-agent..."

# 数据库文件路径
DB_PATH="backend/data/gaokao_shanxi_recruit.db"
DB_URL="https://github.com/Maoshuyong/gaokao-agent/releases/download/v1.0-db/gaokao_shanxi_recruit.db"

# 检查数据库是否已存在
if [ -f "$DB_PATH" ]; then
    echo "✅ 数据库已存在: $DB_PATH"
    echo "   文件大小: $(du -h "$DB_PATH" | cut -f1)"
else
    echo "📥 数据库不存在，正在从 GitHub Release 下载..."
    echo "   URL: $DB_URL"
    
    # 创建目录
    mkdir -p backend/data
    
    # 下载数据库（使用 curl）
    curl -L -o "$DB_PATH" "$DB_URL" --progress-bar
    
    # 验证下载
    if [ -f "$DB_PATH" ]; then
        echo "✅ 数据库下载成功: $DB_PATH"
        echo "   文件大小: $(du -h "$DB_PATH" | cut -f1)"
    else
        echo "❌ 数据库下载失败！"
        exit 1
    fi
fi

# 启动应用
echo "🎯 启动 FastAPI 应用..."
cd backend
uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}
