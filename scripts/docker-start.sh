#!/bin/bash
# ================================
# AutoVoiceCollation Docker 快速启动脚本
# ================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查 Docker 和 Docker Compose
check_dependencies() {
    print_info "检查依赖..."

    if ! command_exists docker; then
        print_error "Docker 未安装！请先安装 Docker。"
        print_info "安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker compose version >/dev/null 2>&1; then
        print_error "Docker Compose 未安装或版本过低！"
        print_info "请安装 Docker Compose v2.0 或更高版本。"
        exit 1
    fi

    print_success "依赖检查通过！"
}

# 检查 GPU 支持
check_gpu() {
    print_info "检查 GPU 支持..."

    if ! command_exists nvidia-smi; then
        print_warning "未检测到 NVIDIA 驱动，将使用 CPU 模式。"
        return 1
    fi

    if ! docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1; then
        print_warning "NVIDIA Docker 运行时未正确配置，将使用 CPU 模式。"
        return 1
    fi

    print_success "检测到 GPU 支持！"
    return 0
}

# 检查并创建 .env 文件
check_env_file() {
    print_info "检查配置文件..."

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            print_warning ".env 文件不存在，正在从 .env.example 复制..."
            cp .env.example .env
            print_success ".env 文件已创建！"
            print_warning "请编辑 .env 文件，配置你的 API Keys："
            print_info "  nano .env"
            print_info "或者："
            print_info "  vim .env"
            echo ""
            read -p "按回车键继续（确保已配置 API Keys）..."
        else
            print_error ".env.example 文件不存在！"
            exit 1
        fi
    else
        print_success "配置文件检查完成！"
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."

    mkdir -p out download temp logs models

    print_success "目录创建完成！"
}

# 构建镜像
build_image() {
    local mode=$1

    if [ "$mode" == "cpu" ]; then
        print_info "构建 CPU 版本镜像..."
        docker compose build autovoicecollation-api-cpu
    else
        print_info "构建 GPU 版本镜像..."
        docker compose build autovoicecollation-api
    fi

    print_success "镜像构建完成！"
}

# 启动服务
start_service() {
    local mode=$1

    if [ "$mode" == "cpu" ]; then
        print_info "启动 CPU 版本服务..."
        docker compose --profile cpu-only up -d
        print_success "服务已启动！"
        print_info "访问地址: http://localhost:8001"
    else
        print_info "启动 GPU 版本服务..."
        docker compose up -d
        print_success "服务已启动！"
        print_info "访问地址: http://localhost:8000"
    fi

    echo ""
    print_info "查看日志: docker compose logs -f"
    print_info "停止服务: docker compose down"
}

# 显示帮助信息
show_help() {
    cat << EOF
AutoVoiceCollation Docker 快速启动脚本

用法: $0 [选项]

选项:
    start           启动服务（自动检测 GPU）
    start-gpu       强制使用 GPU 模式启动
    start-cpu       使用 CPU 模式启动
    stop            停止服务
    restart         重启服务
    logs            查看日志
    build           重新构建镜像
    clean           清理所有容器和镜像
    help            显示此帮助信息

示例:
    $0 start        # 自动检测并启动
    $0 start-cpu    # 强制使用 CPU 模式
    $0 logs         # 查看实时日志
    $0 stop         # 停止服务

EOF
}

# 主函数
main() {
    case "${1:-start}" in
        start)
            check_dependencies
            check_env_file
            create_directories

            if check_gpu; then
                build_image "gpu"
                start_service "gpu"
            else
                print_info "将使用 CPU 模式启动"
                build_image "cpu"
                start_service "cpu"
            fi
            ;;

        start-gpu)
            check_dependencies
            check_env_file
            create_directories
            build_image "gpu"
            start_service "gpu"
            ;;

        start-cpu)
            check_dependencies
            check_env_file
            create_directories
            build_image "cpu"
            start_service "cpu"
            ;;

        stop)
            print_info "停止服务..."
            docker compose down
            print_success "服务已停止！"
            ;;

        restart)
            print_info "重启服务..."
            docker compose restart
            print_success "服务已重启！"
            ;;

        logs)
            docker compose logs -f
            ;;

        build)
            check_dependencies
            print_info "重新构建镜像..."
            docker compose build --no-cache
            print_success "镜像重新构建完成！"
            ;;

        clean)
            print_warning "这将删除所有相关的容器和镜像！"
            read -p "确定要继续吗？(yes/no): " confirm
            if [ "$confirm" == "yes" ]; then
                print_info "清理容器和镜像..."
                docker compose down --rmi all --volumes
                print_success "清理完成！"
            else
                print_info "操作已取消。"
            fi
            ;;

        help|--help|-h)
            show_help
            ;;

        *)
            print_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
