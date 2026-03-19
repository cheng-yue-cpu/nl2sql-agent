#!/bin/bash
# NL2SQL 日志管理脚本

LOG_DIR="/home/admin/.openclaw/workspace/nl2sql-platform/logs"
LOG_FILE="$LOG_DIR/uvicorn.log"

show_help() {
    echo "NL2SQL 日志管理工具"
    echo ""
    echo "用法：$0 [命令]"
    echo ""
    echo "命令:"
    echo "  tail       实时查看日志 (默认)"
    echo "  last       查看最近 50 条日志"
    echo "  error      只查看错误日志"
    echo "  warn       只查看警告日志"
    echo "  clean      清理旧日志（保留最近 1000 行）"
    echo "  size       显示日志文件大小"
    echo "  help       显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0          # 实时查看日志"
    echo "  $0 last     # 查看最近 50 条"
    echo "  $0 error    # 只查看错误"
}

tail_logs() {
    echo "📊 实时查看日志 (Ctrl+C 退出)..."
    tail -f "$LOG_FILE"
}

show_last() {
    echo "📋 最近 50 条日志:"
    tail -50 "$LOG_FILE" | python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if line.startswith('{'):
        try:
            data = json.loads(line)
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(line)
    else:
        print(line)
" 2>/dev/null || tail -50 "$LOG_FILE"
}

show_errors() {
    echo "❌ 错误日志:"
    grep '"level": "error"' "$LOG_FILE" | tail -20 | python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if line.startswith('{'):
        try:
            data = json.loads(line)
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(line)
    else:
        print(line)
" 2>/dev/null || grep '"level": "error"' "$LOG_FILE" | tail -20
}

show_warnings() {
    echo "⚠️  警告日志:"
    grep '"level": "warning"' "$LOG_FILE" | tail -20 | python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if line.startswith('{'):
        try:
            data = json.loads(line)
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(line)
    else:
        print(line)
" 2>/dev/null || grep '"level": "warning"' "$LOG_FILE" | tail -20
}

clean_logs() {
    echo "🧹 清理日志文件..."
    if [ -f "$LOG_FILE" ]; then
        line_count=$(wc -l < "$LOG_FILE")
        if [ "$line_count" -gt 1000 ]; then
            tail -1000 "$LOG_FILE" > "$LOG_FILE.tmp"
            mv "$LOG_FILE.tmp" "$LOG_FILE"
            echo "✅ 已清理到最近 1000 行 (原 $line_count 行)"
        else
            echo "ℹ️  日志文件较小 ($line_count 行)，无需清理"
        fi
    else
        echo "❌ 日志文件不存在"
    fi
}

show_size() {
    echo "📊 日志文件大小:"
    if [ -f "$LOG_FILE" ]; then
        ls -lh "$LOG_FILE" | awk '{print $5, $9}'
        wc -l "$LOG_FILE"
    else
        echo "❌ 日志文件不存在"
    fi
}

# 主逻辑
case "${1:-tail}" in
    tail)
        tail_logs
        ;;
    last)
        show_last
        ;;
    error)
        show_errors
        ;;
    warn|warning)
        show_warnings
        ;;
    clean)
        clean_logs
        ;;
    size)
        show_size
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ 未知命令：$1"
        show_help
        exit 1
        ;;
esac
