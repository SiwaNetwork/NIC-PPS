#!/bin/bash
# Скрипт для принудительной настройки только восходящего фронта PPS
# Работает без изменения драйвера

set -e

PTP_DEVICE="${1:-/dev/ptp0}"
PIN_INDEX="${2:-1}"

echo "🔧 Настройка восходящего фронта PPS для $PTP_DEVICE (пин $PIN_INDEX)"

# Отключаем все существующие настройки
echo "📛 Отключение всех PPS настроек..."
sudo testptp -d "$PTP_DEVICE" -X 0 2>/dev/null || true
sudo testptp -d "$PTP_DEVICE" -X 1 2>/dev/null || true

# Ждем немного
sleep 0.5

# Настраиваем пин только на восходящий фронт (функция 1 = EXTTS input)
echo "🔼 Настройка пина $PIN_INDEX на восходящий фронт..."
sudo testptp -d "$PTP_DEVICE" -L${PIN_INDEX},1

# Проверяем настройку
echo "✅ Проверка настройки..."
sudo testptp -d "$PTP_DEVICE" -l

echo "✅ Настройка завершена!"
echo ""
echo "Для тестирования запустите:"
echo "  sudo testptp -d $PTP_DEVICE -e 10"
echo ""
echo "Вы должны видеть только ОДНО событие на импульс."
