#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.pid"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

if [[ ! -f "$PID_FILE" ]]; then
    warn "PID 文件不存在，服务可能未在运行"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    warn "进程 $PID 已不存在，清理 PID 文件"
    rm -f "$PID_FILE"
    exit 0
fi

info "正在停止服务 (PID: $PID)..."
kill "$PID"

for i in $(seq 1 10); do
    if ! kill -0 "$PID" 2>/dev/null; then
        rm -f "$PID_FILE"
        info "服务已停止"
        exit 0
    fi
    sleep 1
done

warn "服务未响应 SIGTERM，强制终止..."
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
info "服务已强制停止"
