#!/bin/bash
# Watchdog скрипт для мониторинга и автоматического перезапуска phc2sys

WATCHDOG_INTERVAL=5  # Проверка каждые 5 секунд
LOG_FILE="/tmp/phc_watchdog.log"
PID_FILE="/tmp/phc_watchdog.pid"

# Сохраняем PID watchdog
echo $$ > "$PID_FILE"

# Параметры phc2sys
SOURCE_PTP="${1:-/dev/ptp2}"
TARGET_PTP="${2:-/dev/ptp0}"
OFFSET="${3:-0}"
RATE="${4:-16}"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

start_phc2sys() {
    log_message "🚀 Запуск phc2sys: $SOURCE_PTP -> $TARGET_PTP (offset=$OFFSET, rate=$RATE)"
    
    # Убиваем старые процессы
    pkill -9 phc2sys 2>/dev/null
    sleep 1
    
    # Запускаем phc2sys в фоне
    phc2sys -c "$TARGET_PTP" -s "$SOURCE_PTP" -O "$OFFSET" -R "$RATE" -m > /tmp/phc2sys.log 2>&1 &
    PHC_PID=$!
    
    # Проверяем что процесс запустился
    sleep 1
    if kill -0 $PHC_PID 2>/dev/null; then
        log_message "✅ phc2sys запущен (PID: $PHC_PID)"
        echo $PHC_PID > /tmp/phc2sys.pid
        return 0
    else
        log_message "❌ Не удалось запустить phc2sys"
        return 1
    fi
}

check_phc2sys() {
    # Проверяем наличие процесса
    if pgrep -x phc2sys > /dev/null; then
        # Дополнительная проверка - читаем вывод
        if [ -f /tmp/phc2sys.log ]; then
            # Проверяем что лог обновляется (активность за последние 30 секунд)
            if [ -n "$(find /tmp/phc2sys.log -mtime -30s 2>/dev/null)" ]; then
                return 0  # Процесс работает
            fi
        else
            return 0  # Процесс есть, лог пока не важен
        fi
    fi
    return 1  # Процесс не работает
}

log_message "🔍 Watchdog запущен для мониторинга phc2sys"
log_message "📊 Параметры: $SOURCE_PTP -> $TARGET_PTP (offset=$OFFSET, rate=$RATE)"

# Первый запуск
start_phc2sys

# Основной цикл мониторинга
while true; do
    sleep $WATCHDOG_INTERVAL
    
    if ! check_phc2sys; then
        log_message "⚠️ phc2sys не работает! Перезапускаем..."
        start_phc2sys
    fi
done
