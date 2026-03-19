#!/bin/bash
# 实时查看 NL2SQL 平台日志

LOG_FILE="/home/admin/.openclaw/workspace/nl2sql-platform/logs/uvicorn.log"

echo "========================================"
echo "📊 NL2SQL Platform - 实时日志查看"
echo "========================================"
echo "日志文件：$LOG_FILE"
echo "按 Ctrl+C 退出"
echo "========================================"
echo ""

tail -f "$LOG_FILE" | while read line; do
    # 解析 JSON 日志并格式化输出
    if echo "$line" | grep -q "^{"; then
        # JSON 格式日志
        timestamp=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('timestamp','')[:19])" 2>/dev/null)
        level=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('level','').upper())" 2>/dev/null)
        event=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('event',''))" 2>/dev/null)
        
        # 颜色输出
        case "$level" in
            "ERROR") color="\033[31m" ;;  # 红色
            "WARNING") color="\033[33m" ;; # 黄色
            "INFO") color="\033[32m" ;;   # 绿色
            "DEBUG") color="\033[36m" ;;  # 青色
            *) color="\033[0m" ;;
        esac
        
        printf "${color}[%s] %-7s\033[0m %s\n" "$timestamp" "$level" "$event"
    else
        # 普通日志（uvicorn 访问日志）
        echo "$line"
    fi
done
