#!/bin/bash
# Скрипт для применения патча драйвера igc после перезагрузки на ядро 6.8.0

set -e

echo "🔧 Применение патча драйвера igc после перезагрузки"
echo "===================================================="

# Проверка текущей версии ядра
KERNEL_VERSION=$(uname -r)
echo "Текущее ядро: $KERNEL_VERSION"

if [[ ! "$KERNEL_VERSION" =~ ^6\.8\.0 ]]; then
    echo "❌ Ошибка: Необходимо загрузиться с ядра 6.8.0"
    echo "Текущее ядро: $KERNEL_VERSION"
    echo ""
    echo "Пожалуйста, перезагрузитесь и выберите ядро 6.8.0-84 в меню GRUB"
    exit 1
fi

echo "✅ Загружено правильное ядро: $KERNEL_VERSION"

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Этот скрипт должен запускаться с правами root"
    exit 1
fi

# Распаковка исходников ядра
echo ""
echo "📦 Распаковка исходников ядра..."
cd /usr/src
if [ ! -d "linux-source-6.8.0" ]; then
    tar -xjf linux-source-6.8.0.tar.bz2
fi
cd linux-source-6.8.0

# Создание патча для igc
echo ""
echo "📝 Создание файла патча..."
cat > /tmp/igc_rising_edge_fix.patch << 'EOF'
--- a/drivers/net/ethernet/intel/igc/igc_ptp.c
+++ b/drivers/net/ethernet/intel/igc/igc_ptp.c
@@ -450,12 +450,18 @@ static int igc_ptp_feature_enable_i225(struct ptp_clock_info *ptp,
 	case PTP_CLK_REQ_EXTTS:
 		if (rq->extts.index >= IGC_N_EXTTS)
 			return -EINVAL;
+		
+		/* Force rising edge only for PPS signals */
+		rq->extts.flags &= ~PTP_FALLING_EDGE;
+		rq->extts.flags |= PTP_RISING_EDGE;
+		
 		if (on) {
 			igc_pin_extts(igc, rq->extts.index);
 			igc_write_flush(hw);
 		} else {
 			igc_pin_disable(igc, rq->extts.index);
 		}
+		
+		adapter->perout[rq->extts.index].flags = rq->extts.flags;
 		return 0;
 	case PTP_CLK_REQ_PEROUT:
 		if (rq->perout.index >= IGC_N_PEROUT)
EOF

echo "✅ Патч создан"

# Применение патча
echo ""
echo "🔨 Применение патча к драйверу igc..."
if patch -p1 --dry-run < /tmp/igc_rising_edge_fix.patch >/dev/null 2>&1; then
    patch -p1 < /tmp/igc_rising_edge_fix.patch
    echo "✅ Патч применен успешно"
else
    echo "⚠️ Не удалось применить патч автоматически"
    echo "Возможно, патч уже применен или структура файла отличается"
fi

# Подготовка конфигурации ядра
echo ""
echo "⚙️ Подготовка конфигурации ядра..."
make oldconfig < /dev/null
make modules_prepare

# Компиляция модуля igc
echo ""
echo "🔨 Компиляция драйвера igc..."
make M=drivers/net/ethernet/intel/igc modules

# Резервная копия старого драйвера
echo ""
echo "💾 Создание резервной копии старого драйвера..."
DRIVER_PATH="/lib/modules/$KERNEL_VERSION/kernel/drivers/net/ethernet/intel/igc/igc.ko"
if [ -f "$DRIVER_PATH" ]; then
    cp "$DRIVER_PATH" "${DRIVER_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Резервная копия создана"
fi

# Установка нового драйвера
echo ""
echo "📥 Установка пропатченного драйвера..."
cp drivers/net/ethernet/intel/igc/igc.ko "$DRIVER_PATH"
depmod -a

echo "✅ Драйвер установлен"

# Перезагрузка драйвера
echo ""
echo "🔄 Перезагрузка драйвера igc..."

# Получаем список интерфейсов
INTERFACES=$(ls /sys/class/net/ | while read iface; do
    if [ -L "/sys/class/net/$iface/device/driver" ]; then
        driver=$(basename $(readlink "/sys/class/net/$iface/device/driver"))
        if [ "$driver" = "igc" ]; then
            echo "$iface"
        fi
    fi
done)

# Отключаем интерфейсы
for iface in $INTERFACES; do
    echo "  Отключение $iface..."
    ip link set "$iface" down
done

# Выгружаем драйвер
modprobe -r igc 2>/dev/null || true
sleep 2

# Загружаем новый драйвер
modprobe igc

# Включаем интерфейсы
for iface in $INTERFACES; do
    echo "  Включение $iface..."
    ip link set "$iface" up
    sleep 1
done

echo ""
echo "✅ Драйвер перезагружен"

# Проверка
echo ""
echo "🔍 Проверка установки..."
if lsmod | grep -q igc; then
    echo "✅ Драйвер igc загружен"
    modinfo igc | grep -E "filename|srcversion"
else
    echo "❌ Драйвер igc не загружен"
    exit 1
fi

# Проверка PTP устройств
if ls /dev/ptp* >/dev/null 2>&1; then
    echo "✅ PTP устройства обнаружены:"
    ls -la /dev/ptp*
else
    echo "⚠️ PTP устройства не найдены"
fi

echo ""
echo "=========================================="
echo "✅ Патч успешно применен!"
echo "=========================================="
echo ""
echo "Теперь PPS будет использовать только восходящий фронт."
echo ""
echo "Для тестирования запустите:"
echo "  sudo testptp -d /dev/ptp0 -L1,1  # Включить PPS input"
echo "  sudo testptp -d /dev/ptp0 -e 10  # Читать 10 событий"
echo ""
echo "Вы должны видеть только ОДНО событие на каждый PPS импульс."
echo ""
