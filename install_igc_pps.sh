#!/bin/bash

# Скрипт установки драйвера Intel IGC с поддержкой PPS
# Автор: Assistant
# Дата: $(date +%Y-%m-%d)

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция вывода сообщений
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    error "Запустите скрипт с правами root: sudo $0"
fi

# Версия драйвера
DRIVER_VERSION="5.4.0-7642.46"

log "Начинаем установку драйвера Intel IGC с поддержкой PPS"
log "Версия драйвера: $DRIVER_VERSION"

# Шаг 1: Скачивание и распаковка драйвера
log "Шаг 1: Скачивание драйвера..."
cd /tmp
if [ -f "intel-igc-ppsfix_ubuntu.zip" ]; then
    rm -f intel-igc-ppsfix_ubuntu.zip
fi
if [ -d "intel-igc-ppsfix" ]; then
    rm -rf intel-igc-ppsfix
fi

wget -q --show-progress https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip || error "Не удалось скачать драйвер"
unzip -q intel-igc-ppsfix_ubuntu.zip || error "Не удалось распаковать архив"
cd intel-igc-ppsfix

# Шаг 2: Удаление старого драйвера (если установлен)
log "Шаг 2: Удаление старого драйвера..."
if dkms status | grep -q "igc"; then
    dkms remove igc -v $DRIVER_VERSION 2>/dev/null || warning "Старый драйвер не найден"
else
    log "Старый драйвер не установлен"
fi

# Шаг 3: Добавление и сборка нового драйвера
log "Шаг 3: Добавление нового драйвера в DKMS..."
dkms add . || error "Не удалось добавить драйвер в DKMS"

log "Сборка драйвера..."
dkms build --force igc -v $DRIVER_VERSION || error "Не удалось собрать драйвер"

log "Установка драйвера..."
dkms install --force igc -v $DRIVER_VERSION || error "Не удалось установить драйвер"

# Шаг 4: Замена оригинального модуля ядра
log "Шаг 4: Замена оригинального модуля ядра..."
KERNEL_VERSION=$(uname -r)
ORIG_MODULE="/lib/modules/$KERNEL_VERSION/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst"
DKMS_MODULE="/lib/modules/$KERNEL_VERSION/updates/dkms/igc.ko.zst"

if [ -f "$ORIG_MODULE" ]; then
    cp "$ORIG_MODULE" "${ORIG_MODULE}.bak" || error "Не удалось создать резервную копию"
    log "Резервная копия создана: ${ORIG_MODULE}.bak"
fi

if [ -f "$DKMS_MODULE" ]; then
    cp "$DKMS_MODULE" "$ORIG_MODULE" || error "Не удалось заменить модуль"
    log "Модуль успешно заменён"
else
    error "Не найден скомпилированный DKMS модуль"
fi

# Шаг 5: Обновление initramfs
log "Шаг 5: Обновление модулей ядра..."
depmod -a || error "Не удалось обновить зависимости модулей"
update-initramfs -u || error "Не удалось обновить initramfs"

# Очистка временных файлов
log "Очистка временных файлов..."
cd /
rm -rf /tmp/intel-igc-ppsfix*

log "✅ Установка завершена успешно!"
log "Для применения изменений требуется перезагрузка."
echo ""
warning "Выполните команду: sudo reboot"
echo ""
log "После перезагрузки запустите: sudo ./configure_pps.sh"