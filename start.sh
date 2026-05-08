#!/bin/bash
# Render 部署脚本：启动时下载数据库文件
# 支持环境变量配置：
#   - DATABASE_URL: 数据库下载URL（必填）
#   - DATABASE_PATH: 数据库保存路径（默认：backend/data/gaokao_shanxi_recruit.db）

# set -e  # 注释掉：数据库下载失败也继续启动应用

echo "🚀 启动 gaokao-agent..."

# 数据库配置（从环境变量读取，提供默认值）
DB_PATH="${DATABASE_PATH:-backend/data/gaokao.db}"
DB_URL="${DATABASE_URL:-http://tecjtbmlo.hn-bkt.clouddn.com/gaokao.db}"

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
    
    # 下载数据库（优先使用 curl，否则用 wget，最后用 Python）
    echo "⏳ 下载中..."
    
    if command -v curl &> /dev/null; then
        curl -L -o "$DB_PATH" "$DB_URL" --progress-bar
    elif command -v wget &> /dev/null; then
        wget -O "$DB_PATH" "$DB_URL"
    else
        echo "    curl/wget 未找到，使用 Python 下载..."
        python3 -c "
import urllib.request
import sys
url = '$DB_URL'
filename = '$DB_PATH'
urllib.request.urlretrieve(url, filename)
print(f'   下载完成: {filename}')
"
    fi
    
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
