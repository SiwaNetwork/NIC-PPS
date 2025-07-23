#!/bin/bash

# PTP NIC Setup Script
# This script configures the PTP device for TimeNIC PCIe card

set -e

echo "🔧 Настройка PTP устройства TimeNIC..."

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   echo "❌ Этот скрипт должен быть запущен с правами root"
   echo "Используйте: sudo $0"
   exit 1
fi

# Проверка наличия устройства PTP
if [ ! -e /dev/ptp0 ]; then
    echo "❌ Устройство /dev/ptp0 не найдено"
    exit 1
fi

# Проверка наличия утилит
for util in testptp ts2phc; do
    if ! command -v "$util" >/dev/null 2>&1; then
        echo "❌ Утилита $util не найдена"
        echo "Установите необходимые утилиты и попробуйте снова"
        exit 1
    fi
done

echo "📡 Настройка PTP пинов..."

# Настройка пинов согласно systemd сервису
echo "  - Настройка пина 0 как вход (external timestamp)..."
/usr/bin/testptp -d /dev/ptp0 -L0,2

echo "  - Настройка периодического выхода 1 Гц..."
/usr/bin/testptp -d /dev/ptp0 -p 1000000000

echo "  - Настройка пина 1 как выход (periodic output)..."
/usr/bin/testptp -d /dev/ptp0 -L1,1

echo "🔄 Запуск ts2phc для синхронизации..."
echo "  Нажмите Ctrl+C для остановки"

# Запуск ts2phc
/usr/sbin/ts2phc -c /dev/ptp0 -s generic --ts2phc.pin_index 1 -m -l 7

echo "✅ Настройка завершена"