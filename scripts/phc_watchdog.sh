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

# Валидация RATE (должен быть >= 1)
if (( $(echo "$RATE <= 0" | bc -l) )); then
    echo "⚠️ Неверный RATE: $RATE, используем значение по умолчанию: 16"
    RATE=16
fi

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

start_phc2sys() {
    log_message "🚀 Запуск phc2sys: $SOURCE_PTP -> $TARGET_PTP (offset=$OFFSET, rate=$RATE)"
    
    # Убиваем старые процессы
    sudo pkill -9 phc2sys 2>/dev/null || true
    sleep 1
    
    # Применяем offset если нужен
    if [ "$OFFSET" != "0" ] && [ -n "$OFFSET" ]; then
        OFFSET_SEC=$(echo "scale=9; $OFFSET/1000000000" | bc -l)
        log_message "🔧 Применение offset: $OFFSET нс ($OFFSET_SEC сек)"
        sudo phc_ctl "$TARGET_PTP" -- adj "$OFFSET_SEC" 2>/dev/null || log_message "⚠️ phc_ctl не удался"
    fi
    
    # Запускаем phc2sys с sudo в фоне (без перенаправления, чтобы видеть вывод в терминале)
    sudo phc2sys -c "$TARGET_PTP" -s "$SOURCE_PTP" -O 0 -R "$RATE" -m &
    PHC_PID=$!
    
    # Проверяем что процесс запустился
    sleep 2
    if sudo pgrep phc2sys > /dev/null 2>&1; then
        log_message "✅ phc2sys запущен успешно (PID: $(sudo pgrep phc2sys))"
        return 0
    else
        log_message "❌ Не удалось запустить phc2sys"
        return 1
    fi
}

check_phc2sys() {
    # Проверяем наличие процесса phc2sys
    if sudo pgrep phc2sys > /dev/null 2>&1; then
        return 0  # Процесс работает
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
