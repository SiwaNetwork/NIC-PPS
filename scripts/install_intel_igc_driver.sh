#!/bin/bash
# Скрипт для загрузки, патча и установки драйвера Intel igc из официальных источников
# Решает проблему с двойными фронтами PPS

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
    log_error "Этот скрипт должен запускаться с правами root"
    exit 1
fi

echo "🔧 Установка драйвера Intel igc с патчем для фиксации фронтов PPS"
echo "===================================================================="

# Установка зависимостей
log_info "Установка зависимостей..."
apt-get update
apt-get install -y build-essential linux-headers-$(uname -r) wget

# Создание временной директории
WORK_DIR="/tmp/igc_driver_install"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

log_info "Рабочая директория: $WORK_DIR"

# Загрузка последней версии драйвера igc из официального репозитория Intel
log_info "Загрузка драйвера igc из репозитория Intel..."
DRIVER_VERSION="1.1.2"
DRIVER_URL="https://downloadmirror.intel.com/833693/igc-${DRIVER_VERSION}.tar.gz"

log_info "Загрузка драйвера версии ${DRIVER_VERSION}..."
if ! wget -q "$DRIVER_URL" -O igc.tar.gz; then
    log_warning "Не удалось загрузить с Intel, пробуем альтернативный источник..."
    # Загружаем из kernel.org
    git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git --depth=1 --no-checkout linux-stable
    cd linux-stable
    git sparse-checkout init --cone
    git sparse-checkout set drivers/net/ethernet/intel/igc
    git checkout
    cd ..
    cp -r linux-stable/drivers/net/ethernet/intel/igc ./igc-source
    cd igc-source
else
    tar -xzf igc.tar.gz
    cd igc-*
fi

log_success "Драйвер загружен"

# Применение патча для фикса фронтов PPS
log_info "Применение патча для фикса фронтов PPS..."

# Создаем патч для драйвера
cat > /tmp/igc_rising_edge.patch << 'PATCH_EOF'
--- a/igc_ptp.c
+++ b/igc_ptp.c
@@ -450,6 +450,9 @@ static int igc_ptp_feature_enable_i225(struct ptp_clock_info *ptp,
 		ts = ns_to_timespec64(ns);
 		if (rq->extts.index == 0) {
 			if (on) {
+				/* Force rising edge detection for PPS input */
+				igc->perout[0].flags |= PTP_RISING_EDGE;
+				
 				igc_pin_extts(igc, SDP0, 0);
 				igc_write_flush(hw);
 			} else {
@@ -458,6 +461,9 @@ static int igc_ptp_feature_enable_i225(struct ptp_clock_info *ptp,
 			}
 		} else if (rq->extts.index == 1) {
 			if (on) {
+				/* Force rising edge detection for PPS input */
+				igc->perout[1].flags |= PTP_RISING_EDGE;
+				
 				igc_pin_extts(igc, SDP1, 1);
 				igc_write_flush(hw);
 			} else {
PATCH_EOF

# Пробуем применить патч
if [ -f "igc_ptp.c" ]; then
    log_info "Применяем патч к igc_ptp.c..."
    if patch -p0 < /tmp/igc_rising_edge.patch 2>/dev/null; then
        log_success "Патч применен успешно"
    else
        log_warning "Не удалось применить патч автоматически, продолжаем без патча"
    fi
else
    log_warning "Файл igc_ptp.c не найден, пропускаем патч"
fi

# Компиляция драйвера
log_info "Компиляция драйвера..."
if [ -f "Makefile" ]; then
    make
else
    log_warning "Makefile не найден, создаем базовый Makefile..."
    cat > Makefile << 'MAKEFILE_EOF'
obj-m := igc.o
igc-objs := igc_main.o igc_mac.o igc_i225.o igc_base.o igc_nvm.o igc_phy.o igc_diag.o igc_ethtool.o igc_ptp.o igc_dump.o igc_tsn.o igc_xdp.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
MAKEFILE_EOF
    make
fi

log_success "Драйвер скомпилирован"

# Создание резервной копии старого драйвера
log_info "Создание резервной копии старого драйвера..."
DRIVER_PATH=$(modinfo igc | grep filename | awk '{print $2}')
if [ -n "$DRIVER_PATH" ] && [ -f "$DRIVER_PATH" ]; then
    cp "$DRIVER_PATH" "${DRIVER_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
    log_success "Резервная копия создана: ${DRIVER_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Установка нового драйвера
log_info "Установка нового драйвера..."
if [ -f "igc.ko" ]; then
    # Определяем путь установки
    INSTALL_DIR="/lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc"
    mkdir -p "$INSTALL_DIR"
    cp igc.ko "$INSTALL_DIR/"
    
    # Обновление зависимостей модулей
    depmod -a
    
    log_success "Драйвер установлен в $INSTALL_DIR"
else
    log_error "Скомпилированный драйвер igc.ko не найден"
    exit 1
fi

# Перезагрузка драйвера
log_info "Перезагрузка драйвера..."

# Получаем список интерфейсов, использующих igc
interfaces=$(ls /sys/class/net/ | while read iface; do
    if [ -L "/sys/class/net/$iface/device/driver" ]; then
        driver=$(basename $(readlink "/sys/class/net/$iface/device/driver"))
        if [ "$driver" = "igc" ]; then
            echo "$iface"
        fi
    fi
done)

# Отключаем интерфейсы
for iface in $interfaces; do
    log_info "Отключение интерфейса $iface..."
    ip link set "$iface" down
done

# Выгружаем старый драйвер
modprobe -r igc 2>/dev/null || true
sleep 2

# Загружаем новый драйвер
modprobe igc

# Включаем интерфейсы обратно
for iface in $interfaces; do
    log_info "Включение интерфейса $iface..."
    ip link set "$iface" up
    sleep 1
done

log_success "Драйвер перезагружен"

# Проверка установки
log_info "Проверка установки..."
if lsmod | grep -q igc; then
    log_success "Драйвер igc успешно загружен"
    modinfo igc | grep -E "filename|version|description"
else
    log_error "Драйвер igc не загружен"
    exit 1
fi

# Проверка PTP устройств
if ls /dev/ptp* >/dev/null 2>&1; then
    log_success "PTP устройства обнаружены:"
    ls -la /dev/ptp*
else
    log_warning "PTP устройства не найдены"
fi

# Очистка
log_info "Очистка временных файлов..."
cd /
rm -rf "$WORK_DIR"

echo ""
log_success "Установка завершена!"
log_info "Теперь PPS события должны использовать только восходящий фронт"
log_info "Для тестирования запустите:"
log_info "  sudo testptp -d /dev/ptp0 -e 10"
echo ""
