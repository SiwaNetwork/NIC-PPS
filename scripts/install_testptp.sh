#!/bin/bash

# Скрипт установки testptp согласно гайду TimeNIC

set -e

echo "📦 Установка testptp..."

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   echo "❌ Этот скрипт должен быть запущен с правами root"
   echo "Используйте: sudo $0"
   exit 1
fi

# Создание временной директории
cd /tmp
mkdir -p testptp_build && cd testptp_build

# Загрузка исходников
echo "📥 Загрузка исходников testptp..."
wget -q https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/tools/testing/selftests/ptp/testptp.c
if [ $? -ne 0 ]; then
    echo "❌ Ошибка загрузки testptp.c"
    exit 1
fi

wget -q https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/include/uapi/linux/ptp_clock.h
if [ $? -ne 0 ]; then
    echo "❌ Ошибка загрузки ptp_clock.h"
    exit 1
fi

# Копирование заголовочного файла
echo "📋 Копирование ptp_clock.h..."
cp ptp_clock.h /usr/include/linux/

# Компиляция
echo "🔨 Компиляция testptp..."
gcc -Wall -lrt testptp.c -o testptp
if [ $? -ne 0 ]; then
    echo "❌ Ошибка компиляции testptp"
    echo "Убедитесь, что установлен gcc: apt install gcc"
    exit 1
fi

# Установка
echo "📦 Установка testptp в /usr/bin/..."
cp testptp /usr/bin/
chmod +x /usr/bin/testptp

# Проверка установки
if command -v testptp >/dev/null 2>&1; then
    echo "✅ testptp успешно установлен!"
    echo ""
    echo "Проверка версии:"
    testptp --help | head -n 1
else
    echo "❌ Ошибка: testptp не найден после установки"
    exit 1
fi

# Очистка
cd /
rm -rf /tmp/testptp_build

echo ""
echo "✨ Установка завершена!"
echo "Теперь вы можете использовать testptp для настройки TimeNIC"