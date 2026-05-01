#!/bin/bash
# Render 部署脚本：启动时下载数据库文件
# 支持环境变量配置：
#   - DATABASE_URL: 数据库下载URL（必填）
#   - DATABASE_PATH: 数据库保存路径（默认：backend/data/gaokao_shanxi_recruit.db）

set -e  # 任何错误都退出

echo "🚀 启动 gaokao-agent..."

# 数据库配置（从环境变量读取，提供默认值）
DB_PATH="${DATABASE_PATH:-backend/data/gaokao_shanxi_recruit.db}"
DB_URL="${DATABASE_URL:-http://tecjtbmlo.hn-bkt.clouddn.com/gaokao_shanxi_recruit.db}"

# 检查环境变量
if [ -z "$DB_URL" ]; then
    echo "❌ 错误：未设置 DATABASE_URL 环境变量"
    echo "   请在 Render 控制台设置 DATABASE_URL"
    echo "   例如：https://example.com/gaokao_shanxi_recruit.db"
    exit 1
fi

# 检查数据库是否已存在
if [ -f "$DB_PATH" ]; then
    echo "✅ 数据库已存在: $DB_PATH"
    echo "   文件大小: $(du -h "$DB_PATH" | cut -f1)"
else
    echo "📥 数据库不存在，正在下载..."
    echo "   URL: $DB_URL"
    echo "   保存至: $DB_PATH"
    
    # 创建目录
    mkdir -p "$(dirname "$DB_PATH")"
    
    # 下载数据库（使用 curl，显示进度条）
    echo "⏳ 下载中..."
    curl -L -o "$DB_PATH" "$DB_URL" --progress-bar
    
    # 验证下载
    if [ -f "$DB_PATH" ]; then
        FILE_SIZE=$(du -h "$DB_PATH" | cut -f1)
        echo "✅ 数据库下载成功!"
        echo "   路径: $DB_PATH"
        echo "   大小: $FILE_SIZE"
    else
        echo "❌ 数据库下载失败！"
        echo "   请检查 DATABASE_URL 是否正确"
        echo "   当前 URL: $DB_URL"
        exit 1
    fi
fi

# 启动应用
echo ""
echo "🎯 启动 FastAPI 应用..."
cd backend
uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}
