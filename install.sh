#!/bin/bash
# TG-Content-Bot-Pro 一键安装脚本
# 全面安装: bash <(curl -fsSL https://raw.githubusercontent.com/liwoyuandiane/TG-Content-Bot-Pro/main/install.sh)

set -e

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
print_step() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

command_exists() { command -v "$1" >/dev/null 2>&1; }

# 检查是否是卸载模式
is_uninstall() {
    [ "$1" = "uninstall" ] || [ "$1" = "--uninstall" ] || [ "$1" = "-u" ]
}

# 卸载功能
uninstall() {
    clear
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║     TG-Content-Bot-Pro 卸载程序                ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    
    DEFAULT_DIR="$HOME/TG-Content-Bot-Pro"
    read -p "安装目录 [默认: $DEFAULT_DIR]: " INSTALL_DIR
    INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_DIR}
    
    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "目录不存在: $INSTALL_DIR"
        exit 1
    fi
    
    echo ""
    print_warning "即将删除以下内容："
    echo "  - 项目目录: $INSTALL_DIR"
    echo "  - 所有配置文件(.env)"
    echo "  - 所有下载的文件"
    echo "  - Python 虚拟环境"
    echo ""
    print_error "⚠️  MongoDB 数据库不会被删除，需要手动清理"
    echo ""
    
    read -p "确认删除? 输入 'yes' 继续: " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        print_info "已取消卸载"
        exit 0
    fi
    
    print_step "停止运行中的机器人"
    
    # 停止运行中的机器人进程
    if command_exists pgrep && pgrep -f "python.*main" >/dev/null; then
        print_info "检测到运行中的机器人进程，正在停止..."
        pkill -f "python.*main" || true
        sleep 2
        print_success "机器人已停止"
    else
        print_info "未检测到运行中的机器人"
    fi
    
    print_step "删除项目文件"
    
    print_info "删除目录: $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
    print_success "项目文件已删除"
    
    # 删除可能的系统服务
    if [ -f "/etc/systemd/system/tg-content-bot.service" ]; then
        print_info "检测到系统服务，正在删除..."
        if command_exists systemctl; then
            sudo systemctl stop tg-content-bot 2>/dev/null || true
            sudo systemctl disable tg-content-bot 2>/dev/null || true
        fi
        sudo rm -f /etc/systemd/system/tg-content-bot.service
        print_success "系统服务已删除"
    fi
    
    # 删除可能的 cron 任务
    if command_exists crontab; then
        # 检查是否有相关的 cron 任务
        if crontab -l 2>/dev/null | grep -q "TG-Content-Bot-Pro"; then
            print_info "检测到可能的 cron 任务，正在清理..."
            # 创建临时文件去除相关行
            (crontab -l 2>/dev/null | grep -v "TG-Content-Bot-Pro") | crontab -
            print_success "cron 任务已清理"
        fi
    fi
    
    echo ""
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_success "  卸载完成！"
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    print_info "提示："
    echo "  - MongoDB 数据库数据未删除"
    echo "  - 如需删除数据库，请登录 MongoDB Atlas 手动删除"
    echo ""
    
    exit 0
}

# 检查环境依赖
check_dependencies() {
    print_step "检查环境依赖"
    
    # 收集缺少的依赖
    missing_packages=()
    
    # 检查 Python 3
    if ! command_exists python3; then
        print_error "未找到 Python 3"
        missing_packages+=("python3")
    else
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION"
    fi
    
    # 检查 pip
    if ! command_exists pip3; then
        print_warning "未找到 pip3"
        missing_packages+=("python3-pip")
    else
        print_success "pip3"
    fi
    
    # 检查 venv 和 ensurepip
    PYTHON_MAJOR_MINOR=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "3")
    if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
        print_warning "未找到 python3-venv"
        missing_packages+=("python${PYTHON_MAJOR_MINOR}-venv")
    else
        print_success "python3-venv"
    fi
    
    # 检查 git
    if ! command_exists git; then
        print_warning "未找到 git"
        missing_packages+=("git")
    else
        print_success "git"
    fi
    
    # 检查 ffmpeg
    if ! command_exists ffmpeg; then
        print_warning "未找到 ffmpeg（视频处理需要）"
        missing_packages+=("ffmpeg")
    else
        print_success "ffmpeg"
    fi
    
    # 如果有缺少的包，提示安装
    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo ""
        print_warning "缺少以下依赖: ${missing_packages[*]}"
        echo ""
        
        while true; do
            read -p "是否自动安装缺少的依赖? [Y/n] " -n 1 -r
            echo
            case $REPLY in
                [Yy]* ) 
                    print_info "正在安装依赖..."
                    
                    # 检测包管理器
                    if command_exists apt; then
                        sudo apt update && sudo apt install -y ${missing_packages[*]}
                    elif command_exists dnf; then
                        sudo dnf install -y ${missing_packages[*]}
                    elif command_exists yum; then
                        sudo yum install -y ${missing_packages[*]}
                    else
                        print_error "不支持的包管理器，请手动安装: ${missing_packages[*]}"
                        exit 1
                    fi
                    
                    print_success "依赖安装完成"
                    break
                    ;;
                [Nn]* ) 
                    print_error "缺少必要依赖，无法继续"
                    echo "请手动安装以下依赖: ${missing_packages[*]}"
                    exit 1
                    ;;
                * ) 
                    print_warning "请输入 Y(是) 或 N(否)"
                    ;;
            esac
        done
    fi
}

# 克隆项目代码
clone_repository() {
    local install_dir="$1"
    
    print_step "克隆项目代码"
    
    if [ -d "$install_dir/.git" ]; then
        print_info "目录已包含 git 仓库，更新代码..."
        cd "$install_dir"
        git pull origin main
    else
        print_info "克隆代码到: $install_dir"
        git clone https://github.com/liwoyuandiane/TG-Content-Bot-Pro.git "$install_dir"
        cd "$install_dir"
    fi
    
    print_success "代码克隆完成"
}

# 设置 Python 环境
setup_python_environment() {
    print_step "设置 Python 环境"
    
    print_info "创建虚拟环境..."
    python3 -m venv venv
    
    print_info "激活虚拟环境并安装依赖..."
    source venv/bin/activate
    pip install --upgrade pip >/dev/null 2>&1
    pip install -r requirements.txt
    
    print_success "Python 依赖安装完成"
}

# 收集环境变量
collect_environment_variables() {
    print_step "配置环境变量"
    
    echo ""
    print_info "请输入以下必需的 Telegram 配置信息："
    echo ""
    
    # 必需变量
    read -p "API_ID (从 my.telegram.org 获取): " API_ID
    while [ -z "$API_ID" ]; do
        print_error "API_ID 不能为空"
        read -p "API_ID (从 my.telegram.org 获取): " API_ID
    done
    
    read -p "API_HASH (从 my.telegram.org 获取): " API_HASH
    while [ -z "$API_HASH" ]; do
        print_error "API_HASH 不能为空"
        read -p "API_HASH (从 my.telegram.org 获取): " API_HASH
    done
    
    read -p "BOT_TOKEN (从 @BotFather 获取): " BOT_TOKEN
    while [ -z "$BOT_TOKEN" ]; do
        print_error "BOT_TOKEN 不能为空"
        read -p "BOT_TOKEN (从 @BotFather 获取): " BOT_TOKEN
    done
    
    read -p "AUTH (机器人所有者 Telegram 用户 ID): " AUTH
    while [ -z "$AUTH" ]; do
        print_error "AUTH 不能为空"
        read -p "AUTH (机器人所有者 Telegram 用户 ID): " AUTH
    done
    
    read -p "MONGO_DB (MongoDB 连接字符串): " MONGO_DB
    while [ -z "$MONGO_DB" ]; do
        print_error "MONGO_DB 不能为空"
        read -p "MONGO_DB (MongoDB 连接字符串): " MONGO_DB
    done
    
    echo ""
    print_info "请输入以下可选配置信息（直接回车跳过）："
    echo ""
    
    # 可选变量
    read -p "SESSION (Pyrogram 会话字符串，可选): " SESSION
    read -p "FORCESUB (强制订阅频道用户名，可选): " FORCESUB
    read -p "TELEGRAM_PROXY_SCHEME (代理协议，如 http/socks5，可选): " TELEGRAM_PROXY_SCHEME
    read -p "TELEGRAM_PROXY_HOST (代理主机，可选): " TELEGRAM_PROXY_HOST
    read -p "TELEGRAM_PROXY_PORT (代理端口，可选): " TELEGRAM_PROXY_PORT
    
    # 创建 .env 文件
    cat > .env << EOF
# Telegram API 凭证（从 my.telegram.org 获取）
API_ID=$API_ID
API_HASH=$API_HASH

# Bot Token（从 @BotFather 获取）
BOT_TOKEN=$BOT_TOKEN

# 机器人所有者的 Telegram 用户 ID（从 @userinfobot 获取）
AUTH=$AUTH

# MongoDB 连接字符串
MONGO_DB=$MONGO_DB

# Pyrogram 会话字符串（可选）
SESSION=$SESSION

# 强制订阅频道用户名（可选，不带 @ 符号）
FORCESUB=$FORCESUB

# Telegram 代理配置（可选）
TELEGRAM_PROXY_SCHEME=$TELEGRAM_PROXY_SCHEME
TELEGRAM_PROXY_HOST=$TELEGRAM_PROXY_HOST
TELEGRAM_PROXY_PORT=$TELEGRAM_PROXY_PORT
EOF
    
    print_success ".env 配置文件已创建"
}

# 检查环境变量配置
check_env_config() {
    print_step "检查环境变量配置"
    
    # 检查系统环境变量
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
            # 使用更安全的方式加载环境变量
            if [ -f ".env" ]; then
                # 逐行读取.env文件，避免特殊字符问题
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
            fi
            
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
        else
            print_warning ".env 配置文件不存在"
        fi
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_warning "检测到以下必需的环境变量未配置: ${missing_vars[*]}"
        echo ""
        while true; do
            read -p "是否现在配置环境变量? [Y/n] " -n 1 -r
            echo
            case $REPLY in
                [Yy]* ) 
                    collect_environment_variables
                    break
                    ;;
                [Nn]* ) 
                    print_info "请通过以下方式之一配置环境变量："
                    echo ""
                    print_info "方式一：创建 .env 文件"
                    echo "  1. 复制示例配置文件："
                    echo "     cp .env.example .env"
                    echo "  2. 编辑 .env 文件配置环境变量："
                    echo "     nano .env"
                    echo ""
                    print_info "方式二：设置系统环境变量"
                    echo "  export API_ID=your_api_id"
                    echo "  export API_HASH=your_api_hash"
                    echo "  export BOT_TOKEN=your_bot_token"
                    echo "  export AUTH=your_user_id"
                    echo "  export MONGO_DB=your_mongodb_uri"
                    echo ""
                    print_info "配置完成后重新运行此脚本："
                    echo "  bash install.sh"
                    return 1
                    ;;
                * ) 
                    print_warning "请输入 Y(是) 或 N(否)"
                    ;;
            esac
        done
    fi
    
    print_success "环境变量配置检查通过"
    return 0
}

# 测试 MongoDB 连接
test_mongodb_connection() {
    print_step "测试 MongoDB 连接"
    
    # 使用更安全的方式加载环境变量进行测试
    if [ -f ".env" ]; then
        # 逐行读取.env文件，避免特殊字符问题
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
    fi
    
    print_info "测试 MongoDB 连接..."
    
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
    
    if source venv/bin/activate && python /tmp/test_mongo.py 2>&1 | grep -q "SUCCESS"; then
        print_success "MongoDB 连接成功"
        rm -f /tmp/test_mongo.py
        return 0
    else
        print_error "MongoDB 连接失败"
        echo ""
        print_info "请检查 MONGO_DB 配置是否正确"
        rm -f /tmp/test_mongo.py
        return 1
    fi
}

# 初始化数据库
initialize_database() {
    print_step "初始化数据库"
    
    echo ""
    print_info "数据库初始化可以创建必要的集合和索引"
    echo ""
    
    while true; do
        read -p "是否需要初始化数据库? [Y/n] " -n 1 -r
        echo
        case $REPLY in
            [Yy]* | "" ) 
                print_info "激活虚拟环境..."
                source venv/bin/activate
                
                print_info "执行数据库初始化..."
                
                # 执行数据库初始化脚本
                if python init_database.py; then
                    print_success "数据库初始化成功"
                    return 0
                else
                    print_error "数据库初始化失败"
                    return 1
                fi
                ;;
            [Nn]* ) 
                print_info "跳过数据库初始化"
                print_info "您可以稍后运行以下命令初始化数据库："
                echo "  cd $INSTALL_DIR"
                echo "  source venv/bin/activate"
                echo "  python init_database.py"
                return 0
                ;;
            * ) 
                print_warning "请输入 Y(是) 或 N(否)"
                ;;
        esac
    done
}

# 创建启动脚本
create_start_script() {
    print_step "创建启动脚本"
    
    cat > start.sh << 'EOF'
#!/bin/bash
# TG-Content-Bot-Pro 启动脚本
# 直接运行: ./start.sh
# 后台运行: nohup ./start.sh > bot.log 2>&1 &

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 切换到脚本目录
cd "$SCRIPT_DIR"

# 检查环境变量
check_env_variables() {
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
        echo "错误: 缺少必需的环境变量: ${missing_vars[*]}"
        echo "请配置环境变量后重新运行此脚本"
        echo ""
        echo "方式一：创建 .env 文件"
        echo "  cp .env.example .env"
        echo "  nano .env  # 编辑配置"
        echo ""
        echo "方式二：设置系统环境变量"
        echo "  export API_ID=your_api_id"
        echo "  export API_HASH=your_api_hash"
        echo "  export BOT_TOKEN=your_bot_token"
        echo "  export AUTH=your_user_id"
        echo "  export MONGO_DB=your_mongodb_uri"
        return 1
    fi
    
    return 0
}

# 主程序
main() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🤖 TG-Content-Bot-Pro 启动脚本"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # 检查环境变量
    if ! check_env_variables; then
        exit 1
    fi
    
    # 激活虚拟环境（如果存在）
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✅ 虚拟环境已激活"
    else
        echo "⚠️  未找到虚拟环境，使用系统Python"
    fi
    
    # 测试 MongoDB 连接
    echo "🔍 测试数据库连接..."
    cat > /tmp/test_mongo.py << 'EOF_TEST'
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
EOF_TEST
    
    if python /tmp/test_mongo.py 2>&1 | grep -q "SUCCESS"; then
        echo "✅ 数据库连接成功"
        rm -f /tmp/test_mongo.py
    else
        echo "❌ 数据库连接失败"
        echo "请检查 MONGO_DB 配置是否正确"
        rm -f /tmp/test_mongo.py
        exit 1
    fi
    
    echo ""
    echo "🚀 启动机器人..."
    echo ""
    
    # 启动机器人
    python3 -m main
}

# 执行主程序
main "$@"
EOF
    
    chmod +x start.sh
    print_success "启动脚本已创建"
}

# 检查是否是卸载模式
if is_uninstall "$1"; then
    uninstall
fi

# 主安装流程
main() {
    clear
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     TG-Content-Bot-Pro 一键部署脚本            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # 检测系统
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
        print_info "检测到系统: $PRETTY_NAME"
    else
        print_error "无法识别的系统"
        exit 1
    fi
    
    # 选择安装目录
    DEFAULT_DIR="$HOME/TG-Content-Bot-Pro"
    echo ""
    read -p "安装目录 [默认: $DEFAULT_DIR]: " INSTALL_DIR
    INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_DIR}
    
    # 创建目录
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # 检查环境依赖
    check_dependencies
    
    # 克隆项目代码
    clone_repository "$INSTALL_DIR"
    
    # 设置 Python 环境
    setup_python_environment
    
    # 检查环境变量配置
    if ! check_env_config; then
        print_error "环境变量配置失败，安装无法继续"
        exit 1
    fi
    
    # 测试 MongoDB 连接
    if ! test_mongodb_connection; then
        print_error "MongoDB 连接测试失败，安装无法继续"
        exit 1
    fi
    
    # 初始化数据库（可选）
    initialize_database
    
    # 创建启动脚本
    create_start_script
    
    # 完成安装
    echo ""
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_success "  TG-Content-Bot-Pro 安装成功！"
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    print_info "安装位置: $INSTALL_DIR"
    echo ""
    print_info "启动机器人:"
    echo "  cd $INSTALL_DIR"
    echo "  ./start.sh"
    echo ""
    print_info "后台运行（推荐）:"
    echo "  cd $INSTALL_DIR"
    echo "  nohup ./start.sh > logs/bot.log 2>&1 &"
    echo ""
    print_info "查看日志:"
    echo "  tail -f $INSTALL_DIR/logs/bot.log"
    echo ""
}

# 执行主程序
main "$@"