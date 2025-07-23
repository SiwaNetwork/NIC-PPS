#!/bin/bash

# Simplified PTP NIC Setup Script
# This script performs basic PTP device checks without pin configuration

set -e

echo "🔧 Проверка PTP устройства..."

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

echo "✅ Устройство PTP найдено: /dev/ptp0"

# Проверка возможностей устройства
echo ""
echo "📊 Возможности устройства PTP:"
testptp -d /dev/ptp0 -c

# Получение текущего времени PTP
echo ""
echo "🕐 Текущее время PTP:"
testptp -d /dev/ptp0 -g

# Синхронизация с системным временем (если поддерживается)
echo ""
echo "🔄 Попытка синхронизации с системным временем..."
if testptp -d /dev/ptp0 -s 2>/dev/null; then
    echo "✅ Время синхронизировано"
    echo "🕐 Новое время PTP:"
    testptp -d /dev/ptp0 -g
else
    echo "⚠️  Синхронизация не поддерживается данным устройством"
fi

echo ""
echo "ℹ️  Примечание: Данное PTP устройство имеет ограниченные возможности."
echo "    Для полной функциональности требуется реальная карта TimeNIC с поддержкой:"
echo "    - Программируемых пинов"
echo "    - Внешних временных меток (external timestamps)"
echo "    - Периодических сигналов"
echo ""
echo "✅ Базовая проверка завершена"