#!/bin/bash
# Render 部署脚本：启动时下载数据库文件
# 支持环境变量配置：
#   - DATABASE_DOWNLOAD_URL: 数据库下载URL（GitHub Releases 链接）
#   - DATABASE_PATH: 数据库保存路径（可选，自动判断环境）

# set -e  # 注释掉：数据库下载失败也继续启动应用

echo "🚀 启动 gaokao-agent..."

# 判断运行环境，设置正确的路径
if [ -f "/app/main.py" ]; then
    # Docker 环境（backend/ 代码复制到 /app/）
    echo "🐳 检测到 Docker 环境"
    DB_PATH="${DATABASE_PATH:-/app/data/gaokao.db}"
    WORK_DIR="/app"
else
    # 本地环境
    echo "💻 检测到本地环境"
    DB_PATH="${DATABASE_PATH:-data/gaokao.db}"
    WORK_DIR="."
fi

# 优先使用 DATABASE_DOWNLOAD_URL，兼容旧的 DATABASE_URL
if [ -n "$DATABASE_DOWNLOAD_URL" ]; then
    DB_DOWNLOAD_URL="$DATABASE_DOWNLOAD_URL"
elif [ -n "$DATABASE_URL" ]; then
    # 如果是 http(s) URL，则用作下载链接
    if [[ "$DATABASE_URL" == http* ]]; then
        DB_DOWNLOAD_URL="$DATABASE_URL"
        echo "⚠️ 使用 DATABASE_URL 作为下载链接（建议改名为 DATABASE_DOWNLOAD_URL）"
    else
        # 否则认为是数据库连接字符串，使用默认值
        DB_DOWNLOAD_URL="https://github.com/Maoshuyong/gaokao-agent/releases/download/v1.0.0/gaokao.db"
    fi
else
    DB_DOWNLOAD_URL="https://github.com/Maoshuyong/gaokao-agent/releases/download/v1.0.0/gaokao.db"
fi

# 检查环境变量
if [ -z "$DB_DOWNLOAD_URL" ]; then
    echo "⚠️ 警告：未设置 DATABASE_DOWNLOAD_URL 环境变量"
    echo "   将使用默认 URL: $DB_DOWNLOAD_URL"
fi

# 检查数据库是否已存在
if [ -f "$DB_PATH" ]; then
    echo "✅ 数据库已存在: $DB_PATH"
    echo "   文件大小: $(du -h "$DB_PATH" | cut -f1)"
else
    echo "📥 数据库不存在，正在下载..."
    echo "   URL: $DB_DOWNLOAD_URL"
    echo "   保存至: $DB_PATH"
    
    # 创建目录
    mkdir -p "$(dirname "$DB_PATH")"
    
    # 下载数据库（优先使用 curl，否则用 wget，最后用 Python）
    echo "⏳ 下载中..."
    
    if command -v curl &> /dev/null; then
        curl -L -o "$DB_PATH" "$DB_DOWNLOAD_URL" --progress-bar
    elif command -v wget &> /dev/null; then
        wget -O "$DB_PATH" "$DB_DOWNLOAD_URL"
    else
        echo "    curl/wget 未找到，使用 Python 下载..."
        python3 -c "
import urllib.request
import sys
url = '$DB_DOWNLOAD_URL'
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
        echo "   请检查 DATABASE_DOWNLOAD_URL 是否正确"
        echo "   当前 URL: $DB_DOWNLOAD_URL"
        # Docker 环境：下载失败也继续启动
        if [ "$WORK_DIR" = "/app" ]; then
            echo "⚠️ Docker 环境：继续启动，但数据库工具将不可用..."
        else
            exit 1
        fi
    fi
fi

# 设置 DATABASE_URL（SQLAlchemy 连接字符串）
export DATABASE_URL="sqlite:///$DB_PATH"
echo "🔗 数据库 URL: $DATABASE_URL"

# 启动应用
echo ""
echo "🎯 启动 FastAPI 应用..."
cd "$WORK_DIR"
uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}
