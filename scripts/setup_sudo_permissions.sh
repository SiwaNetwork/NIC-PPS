#!/bin/bash
# Скрипт для настройки sudo прав для PTP утилит
# Позволяет запускать phc2sys, phc_ctl и testptp без пароля

set -e

echo "🔧 Настройка sudo прав для PTP утилит..."
echo ""

# Получаем имя пользователя
USERNAME=$(whoami)

# Путь к файлу sudoers
SUDOERS_FILE="/etc/sudoers.d/ptp-tools"

# Создаем временный файл с правилами
TEMP_FILE=$(mktemp)

cat > "$TEMP_FILE" << EOF
# Разрешаем пользователю $USERNAME запускать PTP утилиты без пароля
# Создано: $(date)
# Для проекта: NIC-PPS

$USERNAME ALL=(ALL) NOPASSWD: /usr/sbin/phc2sys
$USERNAME ALL=(ALL) NOPASSWD: /usr/sbin/phc_ctl
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/testptp
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/pkill -f phc2sys
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/pkill -f phc_watchdog
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/kill *
EOF

echo "📄 Содержимое файла прав:"
cat "$TEMP_FILE"
echo ""

# Проверяем синтаксис
if ! visudo -c -f "$TEMP_FILE" > /dev/null 2>&1; then
    echo "❌ Ошибка в синтаксисе sudoers файла"
    rm "$TEMP_FILE"
    exit 1
fi

echo "✅ Синтаксис проверен"

# Копируем файл в sudoers.d
echo "📝 Создание файла $SUDOERS_FILE..."
sudo cp "$TEMP_FILE" "$SUDOERS_FILE"
sudo chmod 0440 "$SUDOERS_FILE"
sudo chown root:root "$SUDOERS_FILE"

# Удаляем временный файл
rm "$TEMP_FILE"

echo ""
echo "✅ Настройка завершена успешно!"
echo ""
echo "🔍 Проверка настроек..."
echo ""

# Проверяем права
if sudo -n phc2sys --help > /dev/null 2>&1; then
    echo "✅ phc2sys - можно запускать без пароля"
else
    echo "⚠️ phc2sys - требует пароль"
fi

if sudo -n phc_ctl --help > /dev/null 2>&1; then
    echo "✅ phc_ctl - можно запускать без пароля"
else
    echo "⚠️ phc_ctl - требует пароль"
fi

if sudo -n testptp --help > /dev/null 2>&1; then
    echo "✅ testptp - можно запускать без пароля"
else
    echo "⚠️ testptp - требует пароль"
fi

echo ""
echo "🎉 Настройка завершена! Теперь можно запускать GUI без ввода пароля."
