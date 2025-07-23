#!/bin/bash

# Скрипт автоматической установки драйвера Intel IGC с исправлением PPS
# Версия: 1.0
# Дата: 2025-01-23

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка прав суперпользователя
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Этот скрипт должен быть запущен с правами суперпользователя (sudo)"
        exit 1
    fi
}

# Определение дистрибутива
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "Не удалось определить дистрибутив Linux"
        exit 1
    fi
}

# Установка зависимостей
install_dependencies() {
    log_info "Установка необходимых пакетов..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt-get update
        apt-get install -y dkms build-essential linux-headers-$(uname -r) wget unzip pps-tools
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Fedora"* ]]; then
        if command -v dnf &> /dev/null; then
            dnf install -y dkms gcc make kernel-devel-$(uname -r) wget unzip pps-tools
        else
            yum install -y dkms gcc make kernel-devel-$(uname -r) wget unzip pps-tools
        fi
    else
        log_error "Неподдерживаемый дистрибутив: $OS"
        exit 1
    fi
}

# Проверка наличия DKMS
check_dkms() {
    if ! command -v dkms &> /dev/null; then
        log_error "DKMS не установлен. Пожалуйста, установите DKMS и запустите скрипт снова."
        exit 1
    fi
    log_info "DKMS найден: $(dkms --version)"
}

# Скачивание и распаковка драйвера
download_driver() {
    local TEMP_DIR="/tmp/igc-driver-$$"
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"
    
    log_info "Скачивание драйвера..."
    if ! wget -q --show-progress https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip; then
        log_error "Не удалось скачать драйвер"
        exit 1
    fi
    
    log_info "Распаковка архива..."
    if ! unzip -q intel-igc-ppsfix_ubuntu.zip; then
        log_error "Не удалось распаковать архив"
        exit 1
    fi
    
    cd intel-igc-ppsfix
}

# Удаление старой версии драйвера
remove_old_driver() {
    log_info "Проверка наличия старых версий драйвера..."
    
    # Проверяем, установлен ли драйвер в DKMS
    if dkms status | grep -q "igc"; then
        log_warning "Найдена установленная версия драйвера, удаляем..."
        
        # Получаем версию установленного драйвера
        local installed_version=$(dkms status | grep "igc" | awk -F'[,/]' '{print $2}' | head -1)
        
        if [ ! -z "$installed_version" ]; then
            dkms remove igc/$installed_version --all || true
        fi
    fi
    
    # Выгружаем модуль из ядра, если он загружен
    if lsmod | grep -q "^igc"; then
        log_info "Выгружаем модуль igc из ядра..."
        modprobe -r igc || true
    fi
}

# Установка драйвера
install_driver() {
    local DRIVER_VERSION="5.4.0-7642.46"
    
    log_info "Добавление драйвера в DKMS..."
    if ! dkms add .; then
        log_error "Не удалось добавить драйвер в DKMS"
        exit 1
    fi
    
    log_info "Сборка модуля..."
    if ! dkms build igc -v $DRIVER_VERSION; then
        log_error "Не удалось собрать модуль"
        exit 1
    fi
    
    log_info "Установка модуля..."
    if ! dkms install --force igc -v $DRIVER_VERSION; then
        log_error "Не удалось установить модуль"
        exit 1
    fi
    
    log_info "Загрузка модуля..."
    modprobe igc
}

# Проверка установки
verify_installation() {
    log_info "Проверка установки..."
    
    # Проверка DKMS
    if dkms status | grep -q "igc.*installed"; then
        log_info "Драйвер успешно установлен в DKMS"
    else
        log_error "Драйвер не найден в DKMS"
        return 1
    fi
    
    # Проверка загрузки модуля
    if lsmod | grep -q "^igc"; then
        log_info "Модуль igc загружен в ядро"
    else
        log_warning "Модуль igc не загружен. Попытка загрузки..."
        modprobe igc
    fi
    
    # Проверка сетевых интерфейсов
    log_info "Сетевые интерфейсы с драйвером igc:"
    ip link show | grep -B1 "link/ether" | grep -E "^[0-9]+:" || true
    
    # Проверка PPS устройств
    log_info "Проверка устройств PPS:"
    if ls /dev/pps* 2>/dev/null; then
        ls -la /dev/pps*
    else
        log_warning "Устройства PPS не найдены. Они могут появиться после подключения оборудования."
    fi
}

# Настройка автозагрузки
setup_autoload() {
    log_info "Настройка автозагрузки модуля..."
    
    if ! grep -q "^igc$" /etc/modules 2>/dev/null; then
        echo "igc" >> /etc/modules
        log_info "Модуль добавлен в автозагрузку"
    else
        log_info "Модуль уже в автозагрузке"
    fi
    
    # Обновление initramfs для некоторых дистрибутивов
    if command -v update-initramfs &> /dev/null; then
        log_info "Обновление initramfs..."
        update-initramfs -u
    fi
}

# Очистка временных файлов
cleanup() {
    log_info "Очистка временных файлов..."
    rm -rf /tmp/igc-driver-*
}

# Основная функция
main() {
    log_info "Начало установки драйвера Intel IGC с исправлением PPS"
    log_info "Версия ядра: $(uname -r)"
    
    check_root
    detect_distro
    log_info "Обнаружен дистрибутив: $OS $VER"
    
    install_dependencies
    check_dkms
    remove_old_driver
    download_driver
    install_driver
    setup_autoload
    verify_installation
    cleanup
    
    log_info "${GREEN}Установка завершена успешно!${NC}"
    log_info "Драйвер Intel IGC с исправлением PPS установлен и загружен."
    log_info "Для проверки работы PPS используйте: sudo ppstest /dev/pps0"
}

# Обработка прерывания скрипта
trap cleanup EXIT

# Запуск основной функции
main