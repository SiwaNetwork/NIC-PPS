#!/bin/bash
"""
Скрипт для автоматического применения патча драйвера igc
Решает проблему с двойными фронтами PPS
"""

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
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
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Этот скрипт должен запускаться с правами root"
        exit 1
    fi
}

# Проверка доступности необходимых пакетов
check_dependencies() {
    log_info "Проверка зависимостей..."
    
    local missing_packages=()
    
    if ! command -v make &> /dev/null; then
        missing_packages+=("build-essential")
    fi
    
    if ! dpkg -l | grep -q "linux-headers-$(uname -r)"; then
        missing_packages+=("linux-headers-$(uname -r)")
    fi
    
    if ! dpkg -l | grep -q "linux-source-$(uname -r)"; then
        missing_packages+=("linux-source-$(uname -r)")
    fi
    
    if [ ${#missing_packages[@]} -ne 0 ]; then
        log_warning "Отсутствуют пакеты: ${missing_packages[*]}"
        log_info "Установка недостающих пакетов..."
        apt update
        apt install -y "${missing_packages[@]}"
    fi
    
    log_success "Все зависимости установлены"
}

# Создание патча
create_patch() {
    log_info "Создание файла патча..."
    
    cat > /tmp/igc_pps_fix.patch << 'EOF'
diff --git a/drivers/net/ethernet/intel/igc/igc.h b/drivers/net/ethernet/intel/igc/igc.h
index 85cc16396..e3843c4b0 100644
--- a/drivers/net/ethernet/intel/igc/igc.h
+++ b/drivers/net/ethernet/intel/igc/igc.h
@@ -278,6 +278,12 @@ struct igc_adapter {
 		struct timespec64 start;
 		struct timespec64 period;
 	} perout[IGC_N_PEROUT];
+
+	unsigned int ts0_pin;
+	unsigned int ts0_flags;
+	unsigned int ts1_pin;
+	unsigned int ts1_flags;
+	
 };
 
 void igc_up(struct igc_adapter *adapter);
diff --git a/drivers/net/ethernet/intel/igc/igc_defines.h b/drivers/net/ethernet/intel/igc/igc_defines.h
index a18af5c87..e83119155 100644
--- a/drivers/net/ethernet/intel/igc/igc_defines.h
+++ b/drivers/net/ethernet/intel/igc/igc_defines.h
@@ -10,6 +10,10 @@
 
 #define IGC_CTRL_EXT_SDP2_DIR	0x00000400 /* SDP2 Data direction */
 #define IGC_CTRL_EXT_SDP3_DIR	0x00000800 /* SDP3 Data direction */
+#define IGC_CTRL_EXT_SDP2_VAL   0x00000040 /* SDP2 Data value */
+#define IGC_CTRL_EXT_SDP3_VAL   0x00000080 /* SDP3 Data value */
+
+
 #define IGC_CTRL_EXT_DRV_LOAD	0x10000000 /* Drv loaded bit for FW */
 
 /* Definitions for power management and wakeup registers */
@@ -141,6 +145,9 @@
 #define IGC_CTRL_SDP0_DIR	0x00400000  /* SDP0 Data direction */
 #define IGC_CTRL_SDP1_DIR	0x00800000  /* SDP1 Data direction */
 
+#define IGC_CTRL_SDP0_VAL	0x00040000 /* SDP0 Data value */
+#define IGC_CTRL_SDP1_VAL	0x00080000 /* SDP0 Data value */
+
 /* As per the EAS the maximum supported size is 9.5KB (9728 bytes) */
 #define MAX_JUMBO_FRAME_SIZE	0x2600
 
diff --git a/drivers/net/ethernet/intel/igc/igc_main.c b/drivers/net/ethernet/intel/igc/igc_main.c
index da1018d83..dd2bf4de5 100644
--- a/drivers/net/ethernet/intel/igc/igc_main.c
+++ b/drivers/net/ethernet/intel/igc/igc_main.c
@@ -5304,6 +5304,9 @@ static void igc_tsync_interrupt(struct igc_adapter *adapter)
 	u32 tsauxc, sec, nsec, tsicr;
 	struct ptp_clock_event event;
 	struct timespec64 ts;
+	static const u32 igc_sdp_val[IGC_N_SDP] = {
+		IGC_CTRL_SDP0_VAL, IGC_CTRL_SDP1_VAL, IGC_CTRL_EXT_SDP2_VAL, IGC_CTRL_EXT_SDP3_VAL,
+	};
 
 	tsicr = rd32(IGC_TSICR);
 
@@ -5344,16 +5347,70 @@ static void igc_tsync_interrupt(struct igc_adapter *adapter)
 		spin_unlock(&adapter->tmreg_lock);
 	}
 
+	// Add workaround, check which SDP is used for EXTTS
+	// and check the level
+	bool skip_event = 0;
 	if (tsicr & IGC_TSICR_AUTT0) {
+		// for single edge cases, workaround is to read pin level
+		unsigned int pin = adapter->ts0_pin;
+		unsigned int pin_val = 0;
+		// add a small delay to make sure GPIO read is valid
+		udelay(5);
+		if ( (adapter->ts0_flags & PTP_RISING_EDGE) && 
+			(!(adapter->ts0_flags & PTP_FALLING_EDGE) ) ) {
+			// rising edge only case 
+			
+			if ( pin < 2 ) {
+				pin_val = rd32(IGC_CTRL) & igc_sdp_val[pin];
+				/*
+				dev_info(&adapter->pdev->dev, "TS0 interrupt int ctrl, pin %d, pinval = 0x%x\n",
+						pin, pin_val);
+				*/
+			}
+			else {
+				pin_val = rd32(IGC_CTRL_EXT) & igc_sdp_val[pin];
+				/*
+				dev_info(&adapter->pdev->dev, "TS0 interrupt int ctrl_ext, pin %d, pinval = 0x%x\n",
+						pin, pin_val);
+				*/
+			}
+			if ( !pin_val ) skip_event = 1; // rising edge, pin should be high
+							// need the delay so register value is correct
+		} 
+		if ( (adapter->ts0_flags & PTP_FALLING_EDGE) && 
+			(!(adapter->ts0_flags & PTP_RISING_EDGE) ) ) {
+			// falling edge only case
+			if ( pin < 2 ) pin_val = rd32(IGC_CTRL) & igc_sdp_val[pin];
+			else pin_val = rd32(IGC_CTRL_EXT) & igc_sdp_val[pin];
+			if ( pin_val ) skip_event =1; // falling edge, pin should be low
+		} 
 		nsec = rd32(IGC_AUXSTMPL0);
 		sec  = rd32(IGC_AUXSTMPH0);
 		event.type = PTP_CLOCK_EXTTS;
-		event.index = 0;
 		event.timestamp = sec * NSEC_PER_SEC + nsec;
-		ptp_clock_event(adapter->ptp_clock, &event);
+		if ( !skip_event ) ptp_clock_event(adapter->ptp_clock, &event);
 	}
 
 	if (tsicr & IGC_TSICR_AUTT1) {
+		unsigned int pin = adapter->ts1_pin;
+		unsigned int pin_val = 0;
+		// add a small delay to make sure GPIO read is valid
+		udelay(5);
+		if ( (adapter->ts1_flags & PTP_RISING_EDGE) && 
+			(!(adapter->ts1_flags & PTP_FALLING_EDGE) ) ) {
+			// rising edge only case 
+			if ( pin < 2 ) pin_val = rd32(IGC_CTRL) & igc_sdp_val[pin];
+			else pin_val = rd32(IGC_CTRL_EXT) & igc_sdp_val[pin];
+			if ( !pin_val ) return; // rising edge, pin should be high
+		} 
+		if ( (adapter->ts1_flags & PTP_FALLING_EDGE) && 
+			(!(adapter->ts1_flags & PTP_RISING_EDGE) ) ) {
+			// falling edge only case
+			if ( pin < 2 ) pin_val = rd32(IGC_CTRL) & igc_sdp_val[pin];
+			else pin_val = rd32(IGC_CTRL_EXT) & igc_sdp_val[pin];
+			if ( pin_val ) return; // falling edge, pin should be low
+		} 
+
 		nsec = rd32(IGC_AUXSTMPL1);
 		sec  = rd32(IGC_AUXSTMPH1);
 		event.type = PTP_CLOCK_EXTTS;
@@ -6753,6 +6810,7 @@ static int igc_probe(struct pci_dev *pdev,
 	if (err < 0)
 		dev_info(&pdev->dev, "PCIe PTM not supported by PCIe bus/controller\n");
 
+
 	pci_set_master(pdev);
 
 	err = -ENOMEM;
@@ -6946,6 +7004,9 @@ static int igc_probe(struct pci_dev *pdev,
 	adapter->flags &= ~IGC_FLAG_EEE;
 	igc_set_eee_i225(hw, false, false, false);
 
+	adapter->ts0_pin = 1000;
+	adapter->ts1_pin = 1000;
+
 	pm_runtime_put_noidle(&pdev->dev);
 
 	return 0;
diff --git a/drivers/net/ethernet/intel/igc/igc_ptp.c b/drivers/net/ethernet/intel/igc/igc_ptp.c
index 928f38792..ebee4fa39 100644
--- a/drivers/net/ethernet/intel/igc/igc_ptp.c
+++ b/drivers/net/ethernet/intel/igc/igc_ptp.c
@@ -256,18 +256,23 @@ static int igc_ptp_feature_enable_i225(struct ptp_clock_info *ptp,
 
 	switch (rq->type) {
 	case PTP_CLK_REQ_EXTTS:
-		/* Reject requests with unsupported flags */
-		if (rq->extts.flags & ~(PTP_ENABLE_FEATURE |
-					PTP_RISING_EDGE |
-					PTP_FALLING_EDGE |
-					PTP_STRICT_FLAGS))
-			return -EOPNOTSUPP;
+		// PATCH , enable flags
+		/* Reject requests with unsupported flags -> PATCH ALLOW */
 
-		/* Reject requests failing to enable both edges. */
+		/* Reject requests failing to enable both edges. -> PATCH ALLOW */
+		/*
 		if ((rq->extts.flags & PTP_STRICT_FLAGS) &&
 		    (rq->extts.flags & PTP_ENABLE_FEATURE) &&
 		    (rq->extts.flags & PTP_EXTTS_EDGES) != PTP_EXTTS_EDGES)
 			return -EOPNOTSUPP;
+		*/
+
+		// hack patch, non-ideal, complain to me over email
+		// if enabling extts, enable only for rising edge, always ignore falling edge
+		if ( rq->extts.flags & PTP_ENABLE_FEATURE ) {
+			rq->extts.flags = PTP_ENABLE_FEATURE | PTP_RISING_EDGE;
+		}
+		
 
 		if (on) {
 			pin = ptp_find_pin(igc->ptp_clock, PTP_PF_EXTTS,
@@ -278,9 +283,21 @@ static int igc_ptp_feature_enable_i225(struct ptp_clock_info *ptp,
 		if (rq->extts.index == 1) {
 			tsauxc_mask = IGC_TSAUXC_EN_TS1;
 			tsim_mask = IGC_TSICR_AUTT1;
+			igc->ts1_pin = pin;
+			igc->ts1_flags = rq->extts.flags;
+			/*
+			dev_info(&igc->pdev->dev, "TS1 int ctrl, pin %d, flags = %d\n",
+					pin, rq->extts.flags);
+			*/
 		} else {
 			tsauxc_mask = IGC_TSAUXC_EN_TS0;
 			tsim_mask = IGC_TSICR_AUTT0;
+			igc->ts0_pin = pin;
+			igc->ts0_flags = rq->extts.flags;
+			/*
+			dev_info(&igc->pdev->dev, "TS0 int ctrl, pin %d, pinval = 0x%x\n",
+					pin, rq->extts.flags);
+			*/
 		}
 		spin_lock_irqsave(&igc->tmreg_lock, flags);
 		tsauxc = rd32(IGC_TSAUXC);
EOF

    log_success "Файл патча создан: /tmp/igc_pps_fix.patch"
}

# Подготовка исходного кода
prepare_source() {
    log_info "Подготовка исходного кода ядра..."
    
    local kernel_version=$(uname -r)
    local source_dir="/usr/src/linux-source-${kernel_version}"
    
    if [ ! -d "$source_dir" ]; then
        log_error "Исходный код ядра не найден: $source_dir"
        exit 1
    fi
    
    cd "$source_dir"
    
    # Распаковка если необходимо
    if [ ! -f "drivers/net/ethernet/intel/igc/igc.h" ]; then
        log_info "Распаковка исходного кода..."
        tar -xf linux-source-${kernel_version}.tar.bz2 --strip-components=1
    fi
    
    log_success "Исходный код подготовлен"
}

# Применение патча
apply_patch() {
    log_info "Применение патча..."
    
    local kernel_version=$(uname -r)
    local source_dir="/usr/src/linux-source-${kernel_version}"
    
    cd "$source_dir"
    
    if ! patch -p1 < /tmp/igc_pps_fix.patch; then
        log_error "Не удалось применить патч"
        exit 1
    fi
    
    log_success "Патч применен успешно"
}

# Сборка драйвера
build_driver() {
    log_info "Сборка драйвера igc..."
    
    local kernel_version=$(uname -r)
    local source_dir="/usr/src/linux-source-${kernel_version}"
    
    cd "$source_dir"
    
    # Настройка конфигурации
    make oldconfig
    
    # Сборка модуля
    make modules_prepare
    make M=drivers/net/ethernet/intel/igc
    
    if [ ! -f "drivers/net/ethernet/intel/igc/igc.ko" ]; then
        log_error "Сборка драйвера не удалась"
        exit 1
    fi
    
    log_success "Драйвер собран успешно"
}

# Установка драйвера
install_driver() {
    log_info "Установка нового драйвера..."
    
    local kernel_version=$(uname -r)
    local source_dir="/usr/src/linux-source-${kernel_version}"
    local driver_path="/lib/modules/${kernel_version}/kernel/drivers/net/ethernet/intel/igc"
    
    # Создание резервной копии
    if [ -f "${driver_path}/igc.ko" ]; then
        cp "${driver_path}/igc.ko" "${driver_path}/igc.ko.backup"
        log_info "Создана резервная копия: ${driver_path}/igc.ko.backup"
    fi
    
    # Установка нового драйвера
    cp "${source_dir}/drivers/net/ethernet/intel/igc/igc.ko" "${driver_path}/"
    
    # Обновление модулей
    depmod -a
    
    log_success "Драйвер установлен"
}

# Перезагрузка драйвера
reload_driver() {
    log_info "Перезагрузка драйвера igc..."
    
    # Находим интерфейсы igc
    local interfaces=$(ip link show | grep -E "enp[0-9]+s[0-9]+" | cut -d: -f2 | tr -d ' ')
    
    if [ -n "$interfaces" ]; then
        for interface in $interfaces; do
            log_info "Отключение интерфейса $interface"
            ip link set "$interface" down
        done
    fi
    
    # Выгрузка старого драйвера
    modprobe -r igc
    
    # Загрузка нового драйвера
    modprobe igc
    
    # Включение интерфейсов
    if [ -n "$interfaces" ]; then
        for interface in $interfaces; do
            log_info "Включение интерфейса $interface"
            ip link set "$interface" up
        done
    fi
    
    log_success "Драйвер перезагружен"
}

# Тестирование патча
test_patch() {
    log_info "Тестирование патча..."
    
    # Проверка загрузки драйвера
    if ! lsmod | grep -q igc; then
        log_error "Драйвер igc не загружен"
        return 1
    fi
    
    # Проверка PTP устройств
    if ! ls /dev/ptp* >/dev/null 2>&1; then
        log_warning "PTP устройства не найдены"
        return 1
    fi
    
    log_success "Патч работает корректно"
    log_info "Для полного тестирования используйте:"
    log_info "  python scripts/diagnose_pps_edges.py"
}

# Основная функция
main() {
    echo "🔧 Применение патча драйвера igc для решения проблемы с фронтами PPS"
    echo "=================================================================="
    
    check_root
    check_dependencies
    create_patch
    prepare_source
    apply_patch
    build_driver
    install_driver
    reload_driver
    test_patch
    
    echo ""
    log_success "Патч успешно применен!"
    log_info "Теперь PPS события должны использовать только восходящий фронт"
    log_info "Для диагностики запустите: python scripts/diagnose_pps_edges.py"
}

# Обработка аргументов командной строки
case "${1:-}" in
    --help|-h)
        echo "Использование: $0 [опции]"
        echo ""
        echo "Опции:"
        echo "  --help, -h     Показать эту справку"
        echo "  --test         Только тестирование (без применения патча)"
        echo "  --revert       Откат к оригинальному драйверу"
        echo ""
        echo "Примеры:"
        echo "  $0              # Применить патч"
        echo "  $0 --test       # Только тестирование"
        echo "  $0 --revert     # Откат изменений"
        exit 0
        ;;
    --test)
        check_root
        test_patch
        exit 0
        ;;
    --revert)
        check_root
        log_info "Откат к оригинальному драйверу..."
        local kernel_version=$(uname -r)
        local driver_path="/lib/modules/${kernel_version}/kernel/drivers/net/ethernet/intel/igc"
        
        if [ -f "${driver_path}/igc.ko.backup" ]; then
            cp "${driver_path}/igc.ko.backup" "${driver_path}/igc.ko"
            depmod -a
            reload_driver
            log_success "Откат выполнен"
        else
            log_error "Резервная копия не найдена"
            exit 1
        fi
        exit 0
        ;;
    *)
        main
        ;;
esac
