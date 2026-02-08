#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# pay-agent-codereview 一键启动脚本
# 用法: ./start.sh [--check] [-y]
#   --check  仅检测环境，不启动服务
#   -y       跳过所有确认提示，自动安装
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------- 参数解析 ----------
CHECK_ONLY=false
AUTO_YES=false
for arg in "$@"; do
    case "$arg" in
        --check) CHECK_ONLY=true ;;
        -y)      AUTO_YES=true ;;
        *)       echo "未知参数: $arg"; exit 1 ;;
    esac
done

# ---------- 彩色日志 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
step()  { echo -e "${BLUE}[STEP]${NC}  $*"; }

# ---------- 工具函数 ----------
confirm() {
    if $AUTO_YES; then return 0; fi
    read -rp "$1 [y/N]: " answer
    [[ "$answer" =~ ^[Yy]$ ]]
}

version_ge() {
    # 判断 $1 >= $2（语义化版本比较）
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*)  echo "linux" ;;
        *)       echo "unknown" ;;
    esac
}

OS_TYPE="$(detect_os)"

# ============================================================
# 1. 环境检测与安装
# ============================================================
step "检测运行环境..."

# ---------- Python 检测 ----------
check_python() {
    local py_cmd=""
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            py_cmd="$cmd"
            break
        fi
    done

    if [[ -z "$py_cmd" ]]; then
        error "未检测到 Python"
        install_python
        return
    fi

    local py_version
    py_version="$($py_cmd --version 2>&1 | awk '{print $2}')"
    if version_ge "$py_version" "3.10.0"; then
        info "Python $py_version ✓"
        PYTHON_CMD="$py_cmd"
    else
        warn "Python 版本 $py_version 低于最低要求 3.10"
        install_python
    fi
}

install_python() {
    if [[ "$OS_TYPE" == "macos" ]]; then
        echo "  推荐安装方式: brew install python@3.11"
    elif [[ "$OS_TYPE" == "linux" ]]; then
        echo "  推荐安装方式: sudo apt install python3.11 python3.11-venv"
    fi
    if confirm "是否自动安装 Python?"; then
        if [[ "$OS_TYPE" == "macos" ]]; then
            brew install python@3.11
        else
            sudo apt update && sudo apt install -y python3.11 python3.11-venv
        fi
        PYTHON_CMD="python3"
    else
        error "请手动安装 Python 3.10+ 后重试"
        exit 1
    fi
}

# ---------- Node.js 检测 ----------
check_node() {
    if ! command -v node &>/dev/null; then
        error "未检测到 Node.js"
        install_node
        return
    fi

    local node_version
    node_version="$(node --version | sed 's/^v//')"
    if version_ge "$node_version" "18.0.0"; then
        info "Node.js $node_version ✓"
    else
        warn "Node.js 版本 $node_version 低于最低要求 18"
        install_node
    fi
}

install_node() {
    if [[ "$OS_TYPE" == "macos" ]]; then
        echo "  推荐安装方式: brew install node"
    elif [[ "$OS_TYPE" == "linux" ]]; then
        echo "  推荐安装方式: sudo apt install nodejs npm"
    fi
    if confirm "是否自动安装 Node.js?"; then
        if [[ "$OS_TYPE" == "macos" ]]; then
            brew install node
        else
            sudo apt update && sudo apt install -y nodejs npm
        fi
    else
        error "请手动安装 Node.js 18+ 后重试"
        exit 1
    fi
}

# ---------- Claude Code CLI 检测 ----------
check_claude_cli() {
    if command -v claude &>/dev/null; then
        info "Claude Code CLI ✓"
    else
        warn "未检测到 Claude Code CLI"
        if confirm "是否自动安装 Claude Code CLI?"; then
            npm install -g @anthropic-ai/claude-code
            info "Claude Code CLI 安装完成"
        else
            warn "跳过 Claude Code CLI 安装（非必须，但部分功能可能不可用）"
        fi
    fi
}

PYTHON_CMD=""
check_python
check_node
check_claude_cli

echo ""

# ============================================================
# 2. Python 虚拟环境
# ============================================================
step "配置 Python 虚拟环境..."

if [[ ! -d ".venv" ]]; then
    info "创建虚拟环境 .venv ..."
    "$PYTHON_CMD" -m venv .venv
fi

# 激活虚拟环境
# shellcheck disable=SC1091
source .venv/bin/activate
info "虚拟环境已激活: $(which python)"

# 安装依赖
if [[ -f "requirements.txt" ]]; then
    info "安装 Python 依赖..."
    pip install -q -r requirements.txt
    info "Python 依赖安装完成 ✓"
else
    warn "未找到 requirements.txt，跳过依赖安装"
fi

echo ""

# ============================================================
# 3. 环境变量配置
# ============================================================
step "检查环境变量配置..."

ENV_OK=true

if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        warn ".env 文件不存在，从 .env.example 复制..."
        cp .env.example .env
        warn "已创建 .env 文件，请编辑填入真实配置值:"
        warn "  vim .env"
        ENV_OK=false
    else
        error "未找到 .env 和 .env.example 文件"
        ENV_OK=false
    fi
else
    # 检查关键变量是否为占位符
    check_env_var() {
        local var_name="$1"
        local value
        value=$(grep "^${var_name}=" .env 2>/dev/null | cut -d'=' -f2- | xargs)
        if [[ -z "$value" || "$value" == your-* ]]; then
            warn "$var_name 未配置或仍为占位符值"
            ENV_OK=false
        else
            info "$var_name ✓"
        fi
    }

    check_env_var "GITLAB_URL"
    check_env_var "GITLAB_TOKEN"
    check_env_var "CLAUDE_API_KEY"
fi

echo ""

# ============================================================
# 4. 环境检测汇总
# ============================================================
if $CHECK_ONLY; then
    step "环境检测完成（--check 模式）"
    if $ENV_OK; then
        info "所有检查通过，可以启动服务"
    else
        warn "部分配置需要完善，请检查上方提示"
    fi
    exit 0
fi

# ============================================================
# 5. 启动服务
# ============================================================
if ! $ENV_OK; then
    warn "环境变量未完全配置，服务可能无法正常工作"
    if ! confirm "是否仍然启动服务?"; then
        info "请先完善 .env 配置后再启动"
        exit 0
    fi
fi

step "启动 Code Review Agent 服务..."
echo ""
info "服务地址: http://localhost:8000"
info "API 文档: http://localhost:8000/docs"
echo ""

python app/main.py
