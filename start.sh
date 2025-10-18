#!/bin/bash
# TG-Content-Bot-Pro 启动脚本
# 直接运行: ./start.sh
# 后台运行: nohup ./start.sh > bot.log 2>&1 &

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 切换到脚本目录
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 打印函数
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# 检查环境变量
check_env_variables() {
    print_info "检查环境变量配置"
    
    # 检查必需的环境变量
    missing_vars=()
    
    if [ -z "$API_ID" ] || [ -z "$API_HASH" ]; then
        missing_vars+=("API_ID/API_HASH")
    fi
    
    if [ -z "$BOT_TOKEN" ]; then
        missing_vars+=("BOT_TOKEN")
    fi
    
    if [ -z "$AUTH" ]; then
        missing_vars+=("AUTH")
    fi
    
    if [ -z "$MONGO_DB" ]; then
        missing_vars+=("MONGO_DB")
    fi
    
    # 如果系统环境变量不完整，检查.env文件
    if [ ${#missing_vars[@]} -gt 0 ]; then
        if [ -f ".env" ]; then
            print_info "从 .env 文件加载环境变量..."
            # 逐行读取.env文件
            while IFS= read -r line || [[ -n "$line" ]]; do
                # 跳过注释和空行
                if [[ $line =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
                    continue
                fi
                
                # 提取变量名和值
                if [[ $line == *"="* ]]; then
                    var_name="${line%%=*}"
                    var_value="${line#*=}"
                    
                    # 去除变量名和值的前后空格
                    var_name=$(echo "$var_name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    var_value=$(echo "$var_value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    
                    # 导出变量
                    export "$var_name"="$var_value"
                fi
            done < ".env"
            
            # 重新检查环境变量
            missing_vars=()
            if [ -z "$API_ID" ] || [ -z "$API_HASH" ]; then
                missing_vars+=("API_ID/API_HASH")
            fi
            
            if [ -z "$BOT_TOKEN" ]; then
                missing_vars+=("BOT_TOKEN")
            fi
            
            if [ -z "$AUTH" ]; then
                missing_vars+=("AUTH")
            fi
            
            if [ -z "$MONGO_DB" ]; then
                missing_vars+=("MONGO_DB")
            fi
        fi
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "缺少必需的环境变量: ${missing_vars[*]}"
        echo ""
        print_info "请通过以下方式之一配置环境变量："
        echo ""
        print_info "方式一：创建 .env 文件"
        echo "  cp .env.example .env"
        echo "  nano .env  # 编辑配置"
        echo ""
        print_info "方式二：设置系统环境变量"
        echo "  export API_ID=your_api_id"
        echo "  export API_HASH=your_api_hash"
        echo "  export BOT_TOKEN=your_bot_token"
        echo "  export AUTH=your_user_id"
        echo "  export MONGO_DB=your_mongodb_uri"
        return 1
    fi
    
    print_success "环境变量配置检查通过"
    return 0
}

# 测试 MongoDB 连接
test_mongodb_connection() {
    print_info "测试 MongoDB 连接"
    
    cat > /tmp/test_mongo.py << 'EOF'
import sys
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

mongo_uri = os.getenv('MONGO_DB')
if not mongo_uri:
    print("ERROR: MONGO_DB not set")
    sys.exit(1)

try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("SUCCESS")
    sys.exit(0)
except ServerSelectionTimeoutError:
    print("ERROR: Connection timeout")
    sys.exit(1)
except ConnectionFailure as e:
    print(f"ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOF
    
    if python /tmp/test_mongo.py 2>&1 | grep -q "SUCCESS"; then
        print_success "MongoDB 连接成功"
        rm -f /tmp/test_mongo.py
        return 0
    else
        print_error "MongoDB 连接失败"
        echo "请检查 MONGO_DB 配置是否正确"
        rm -f /tmp/test_mongo.py
        return 1
    fi
}

# 主程序
main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     TG-Content-Bot-Pro 启动脚本                ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # 检查环境变量
    if ! check_env_variables; then
        exit 1
    fi
    
    # 激活虚拟环境（如果存在）
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_success "虚拟环境已激活"
    else
        print_warning "未找到虚拟环境，使用系统Python"
    fi
    
    # 测试 MongoDB 连接
    if ! test_mongodb_connection; then
        exit 1
    fi
    
    echo ""
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_success "  启动机器人..."
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # 启动机器人
    python3 -m main
}

# 执行主程序
main "$@"