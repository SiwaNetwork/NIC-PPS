#!/bin/bash

# Скрипт настройки PPS (Pulse Per Second) для Intel IGC
# Автор: Assistant
# Дата: $(date +%Y-%m-%d)

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Функции вывода
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

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    error "Запустите скрипт с правами root: sudo $0"
fi

# Проверка наличия testptp
if ! command -v testptp &> /dev/null; then
    log "Установка пакета linuxptp для работы с PTP..."
    apt-get update -qq
    apt-get install -y -qq linuxptp || error "Не удалось установить linuxptp"
fi

# Поиск сетевого интерфейса IGC
log "Поиск сетевого интерфейса Intel IGC..."
IGC_INTERFACE=$(ip link show | grep -E "enp[0-9]+s[0-9]+" | head -1 | cut -d: -f2 | tr -d ' ')

if [ -z "$IGC_INTERFACE" ]; then
    error "Не найден сетевой интерфейс Intel IGC"
fi

log "Найден интерфейс: $IGC_INTERFACE"

# Проверка драйвера
log "Проверка установленного драйвера..."
DRIVER_INFO=$(ethtool -i $IGC_INTERFACE 2>/dev/null | grep driver: | awk '{print $2}')
if [ "$DRIVER_INFO" != "igc" ]; then
    error "Интерфейс $IGC_INTERFACE не использует драйвер igc"
fi

# Поиск PTP устройства
log "Поиск PTP устройства..."
PTP_DEVICE=$(ethtool -T $IGC_INTERFACE 2>/dev/null | grep "PTP Hardware Clock:" | awk '{print $4}')

if [ -z "$PTP_DEVICE" ]; then
    error "Не найдено PTP устройство для интерфейса $IGC_INTERFACE"
fi

log "Найдено PTP устройство: /dev/$PTP_DEVICE"

# Функция настройки PPS выхода
configure_pps_output() {
    log "Настройка PPS выхода на SMA1 (SDP0)..."
    
    # Назначение SDP0 как выходной пин
    testptp -d /dev/$PTP_DEVICE -L0,2 || error "Не удалось настроить SDP0 как выход"
    log "SDP0 настроен как периодический выход"
    
    # Установка периода 1 Гц (1 секунда = 1000000000 наносекунд)
    testptp -d /dev/$PTP_DEVICE -p 1000000000 || error "Не удалось установить период 1 Гц"
    log "✅ PPS выход настроен на 1 Гц (1PPS) на разъёме SMA1"
}

# Функция настройки PPS входа
configure_pps_input() {
    log "Настройка PPS входа на SMA2 (SDP1)..."
    
    # Назначение SDP1 как входной пин
    testptp -d /dev/$PTP_DEVICE -L1,1 || error "Не удалось настроить SDP1 как вход"
    log "SDP1 настроен для приёма внешних временных меток"
    log "✅ PPS вход настроен на разъёме SMA2"
}

# Функция проверки PPS входа
test_pps_input() {
    log "Тест чтения PPS событий с SMA2..."
    info "Ожидание 5 PPS событий (подключите источник PPS к SMA2)..."
    testptp -d /dev/$PTP_DEVICE -e 5
}

# Главное меню
show_menu() {
    echo ""
    echo -e "${BLUE}=== Настройка PPS для Intel IGC ===${NC}"
    echo "1) Настроить PPS выход (SMA1) - генерация 1PPS"
    echo "2) Настроить PPS вход (SMA2) - приём внешнего PPS"
    echo "3) Настроить оба (выход и вход)"
    echo "4) Проверить PPS вход (прочитать 5 событий)"
    echo "5) Показать информацию о системе"
    echo "0) Выход"
    echo ""
}

# Показать информацию о системе
show_system_info() {
    echo ""
    echo -e "${BLUE}=== Информация о системе ===${NC}"
    echo "Интерфейс: $IGC_INTERFACE"
    echo "PTP устройство: /dev/$PTP_DEVICE"
    echo ""
    echo "Информация о драйвере:"
    modinfo igc | grep -E "version:|filename:" | sed 's/^/  /'
    echo ""
    echo "Информация об интерфейсе:"
    ethtool -i $IGC_INTERFACE | sed 's/^/  /'
    echo ""
}

# Основной цикл
while true; do
    show_menu
    read -p "Выберите опцию: " choice
    
    case $choice in
        1)
            configure_pps_output
            ;;
        2)
            configure_pps_input
            ;;
        3)
            configure_pps_output
            configure_pps_input
            ;;
        4)
            test_pps_input
            ;;
        5)
            show_system_info
            ;;
        0)
            log "Выход из программы"
            exit 0
            ;;
        *)
            warning "Неверный выбор"
            ;;
    esac
    
    echo ""
    read -p "Нажмите Enter для продолжения..."
done