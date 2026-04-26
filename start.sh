#!/bin/sh

export PYTHONUNBUFFERED=1

echo "🚀 启动TG Content Bot Pro应用..."

echo "📂 当前目录: $(pwd)"
echo "🐍 Python版本: $(python3 --version)"

echo "🔍 检查环境变量配置..."

MISSING_VARS=""
[ -z "$API_ID" ] && MISSING_VARS="$MISSING_VARS API_ID"
[ -z "$API_HASH" ] && MISSING_VARS="$MISSING_VARS API_HASH"
[ -z "$BOT_TOKEN" ] && MISSING_VARS="$MISSING_VARS BOT_TOKEN"
[ -z "$AUTH" ] && MISSING_VARS="$MISSING_VARS AUTH"
[ -z "$MONGO_DB" ] && MISSING_VARS="$MISSING_VARS MONGO_DB"
[ -z "$ENCRYPTION_KEY" ] && MISSING_VARS="$MISSING_VARS ENCRYPTION_KEY"

if [ -n "$MISSING_VARS" ]; then
    echo "❌ 缺少必需的环境变量:$MISSING_VARS"
    exit 1
fi

echo "✅ 所有必需的环境变量已配置"

echo "🤖 开始启动机器人应用..."
python3 -m main