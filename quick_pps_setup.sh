#!/bin/bash

# Быстрая настройка PPS для Intel IGC
# Настраивает PPS выход на SMA1 (1PPS)

set -e

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "Запустите с правами root: sudo $0"
    exit 1
fi

# Поиск интерфейса и PTP устройства
INTERFACE=$(ip link show | grep -E "enp[0-9]+s[0-9]+" | head -1 | cut -d: -f2 | tr -d ' ')
if [ -z "$INTERFACE" ]; then
    echo "Ошибка: Не найден Intel IGC интерфейс"
    exit 1
fi

PTP_DEVICE=$(ethtool -T $INTERFACE 2>/dev/null | grep "PTP Hardware Clock:" | awk '{print $4}')
if [ -z "$PTP_DEVICE" ]; then
    echo "Ошибка: Не найдено PTP устройство"
    exit 1
fi

echo "Интерфейс: $INTERFACE"
echo "PTP устройство: /dev/$PTP_DEVICE"
echo ""

# Настройка PPS выхода на SMA1
echo "Настройка PPS выхода на SMA1..."
testptp -d /dev/$PTP_DEVICE -L0,2
testptp -d /dev/$PTP_DEVICE -p 1000000000

echo ""
echo "✅ PPS выход настроен!"
echo "   - Разъём: SMA1"
echo "   - Частота: 1 Гц (1PPS)"
echo ""

# Опционально: настройка входа
read -p "Настроить также PPS вход на SMA2? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Настройка PPS входа на SMA2..."
    testptp -d /dev/$PTP_DEVICE -L1,1
    echo "✅ PPS вход настроен на SMA2"
fi