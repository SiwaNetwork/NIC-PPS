#!/bin/bash

# TimeNIC Setup Script
# Настройка TimeNIC (Intel I226 NIC, SMA, TCXO) на Ubuntu 24.04

set -e

echo "🧾 TimeNIC Setup Script"
echo "Настройка TimeNIC (Intel I226 NIC, SMA, TCXO) на Ubuntu 24.04"
echo ""

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   echo "❌ Этот скрипт должен быть запущен с правами root"
   echo "Используйте: sudo $0"
   exit 1
fi

# Проверка системы
echo "🔍 Проверка системы..."

# Проверка Ubuntu версии
if ! grep -q "Ubuntu 24.04" /etc/os-release; then
    echo "⚠️  Предупреждение: Скрипт тестировался на Ubuntu 24.04"
    echo "Продолжить? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Этап 1: Установка зависимостей
echo ""
echo "🔧 Этап 1: Установка зависимостей..."
apt update
apt install -y openssh-server net-tools gcc vim dkms linuxptp \
    linux-headers-$(uname -r) libgpiod-dev pkg-config build-essential git

# Этап 2: Сборка и установка testptp
echo ""
echo "💻 Этап 2: Сборка и установка testptp..."

cd /tmp
mkdir -p testptp_build && cd testptp_build

# Загрузка исходников
echo "Загрузка исходников testptp..."
wget -q https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/tools/testing/selftests/ptp/testptp.c
wget -q https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/include/uapi/linux/ptp_clock.h
cp ptp_clock.h /usr/include/linux/

# Компиляция
echo "Компиляция testptp..."
gcc -Wall -lrt testptp.c -o testptp

# Установка
echo "Установка testptp..."
cp testptp /usr/bin/
chmod +x /usr/bin/testptp

echo "✅ testptp установлен"

# Этап 3: Проверка PTP устройств
echo ""
echo "🧪 Этап 3: Проверка PTP устройств..."

# Поиск сетевых интерфейсов
interfaces=$(ip link show | grep -E "^[0-9]+:" | awk -F: '{print $2}' | tr -d ' ' | grep -v lo)

echo "Найденные интерфейсы: $interfaces"

for interface in $interfaces; do
    echo "Проверка интерфейса $interface..."
    if command -v ethtool >/dev/null 2>&1; then
        if ethtool -T "$interface" 2>/dev/null | grep -q "PTP Hardware Clock"; then
            echo "✅ PTP устройство найдено на $interface"
            ptp_interface="$interface"
            break
        fi
    fi
done

if [[ -z "$ptp_interface" ]]; then
    echo "⚠️  PTP устройства не найдены"
    echo "Убедитесь, что TimeNIC карта подключена и драйвер загружен"
fi

# Этап 4: Установка драйвера TimeNIC (опционально)
echo ""
echo "🔧 Этап 4: Установка драйвера TimeNIC..."

echo "Хотите установить патченный драйвер TimeNIC? (y/N)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Установка драйвера TimeNIC..."
    
    cd /tmp
    wget -q https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip
    unzip -q intel-igc-ppsfix_ubuntu.zip
    cd intel-igc-ppsfix
    
    # Удаление старого драйвера
    dkms remove igc -v 5.4.0-7642.46 2>/dev/null || true
    
    # Добавление и сборка нового драйвера
    dkms add .
    dkms build --force igc -v 5.4.0-7642.46
    dkms install --force igc -v 5.4.0-7642.46
    
    # Замена оригинального модуля
    kernel_version=$(uname -r)
    cp "/lib/modules/$kernel_version/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst" \
       "/lib/modules/$kernel_version/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst.bak"
    
    cp "/lib/modules/$kernel_version/updates/dkms/igc.ko.zst" \
       "/lib/modules/$kernel_version/kernel/drivers/net/ethernet/intel/igc/"
    
    # Обновление initramfs
    depmod -a
    update-initramfs -u
    
    echo "✅ Драйвер TimeNIC установлен"
    echo "⚠️  Перезагрузите систему для применения изменений"
fi

# Этап 5: Настройка PPS
echo ""
echo "🎯 Этап 5: Настройка PPS..."

if [[ -n "$ptp_interface" ]]; then
    # Находим PTP устройство
    ptp_device=$(ethtool -T "$ptp_interface" 2>/dev/null | grep "PTP Hardware Clock" | awk '{print $4}')
    if [[ -n "$ptp_device" ]]; then
        ptp_path="/dev/ptp$ptp_device"
        
        echo "Настройка PPS для $ptp_path..."
        
        # Включение PPS выхода (SMA1/SDP0)
        echo "Включение PPS выхода на SMA1 (SDP0)..."
        testptp -d "$ptp_path" -L0,2
        testptp -d "$ptp_path" -p 1000000000
        
        # Включение PPS входа (SMA2/SDP1)
        echo "Включение PPS входа на SMA2 (SDP1)..."
        testptp -d "$ptp_path" -L1,1
        
        echo "✅ PPS настроен"
    else
        echo "❌ PTP устройство не найдено"
    fi
else
    echo "⚠️  Пропуск настройки PPS - PTP интерфейс не найден"
fi

# Этап 6: Создание systemd сервиса
echo ""
echo "🛠 Этап 6: Создание systemd сервиса..."

cat > /etc/systemd/system/ptp-nic-setup.service << 'EOF'
[Unit]
Description=Setup PTP on TimeNIC PCIe card
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes

ExecStart=/usr/bin/testptp -d /dev/ptp0 -L0,2
ExecStart=/usr/bin/testptp -d /dev/ptp0 -p 1000000000
ExecStart=/usr/bin/testptp -d /dev/ptp0 -L1,1
ExecStart=/usr/sbin/ts2phc -c /dev/ptp0 -s generic --ts2phc.pin_index 1 -m -l 7

[Install]
WantedBy=multi-user.target
EOF

# Активация сервиса
systemctl daemon-reload
systemctl enable ptp-nic-setup
systemctl start ptp-nic-setup

echo "✅ Systemd сервис создан и активирован"

# Этап 7: Проверка установки
echo ""
echo "🧪 Этап 7: Проверка установки..."

echo "Проверка утилит:"
for util in testptp ts2phc phc_ctl ethtool; do
    if command -v "$util" >/dev/null 2>&1; then
        echo "✅ $util доступен"
    else
        echo "❌ $util не найден"
    fi
done

echo ""
echo "Проверка драйверов:"
if lsmod | grep -q igc; then
    echo "✅ Драйвер igc загружен"
else
    echo "⚠️  Драйвер igc не загружен"
fi

echo ""
echo "Проверка PTP устройств:"
if ls /dev/ptp* 2>/dev/null; then
    echo "✅ PTP устройства найдены"
else
    echo "⚠️  PTP устройства не найдены"
fi

echo ""
echo "Проверка systemd сервиса:"
if systemctl is-active --quiet ptp-nic-setup; then
    echo "✅ ptp-nic-setup сервис активен"
else
    echo "❌ ptp-nic-setup сервис не активен"
fi

# Этап 8: Инструкции по использованию
echo ""
echo "📋 Этап 8: Инструкции по использованию..."

echo ""
echo "🎉 Настройка TimeNIC завершена!"
echo ""
echo "Полезные команды:"
echo "  # Список TimeNIC карт"
echo "  python run.py --cli timenic list-timenics"
echo ""
echo "  # Информация о карте"
echo "  python run.py --cli timenic info $ptp_interface"
echo ""
echo "  # Настройка PPS"
echo "  python run.py --cli timenic set-pps $ptp_interface --mode both"
echo ""
echo "  # Мониторинг"
echo "  python run.py --cli timenic monitor $ptp_interface --interval 1"
echo ""
echo "  # Чтение PPS событий"
echo "  python run.py --cli timenic read-pps /dev/ptp0 --count 5"
echo ""
echo "  # Запуск синхронизации PHC"
echo "  python run.py --cli timenic start-phc-sync $ptp_interface"
echo ""
echo "Документация: docs/TIMENIC_SETUP.md"
echo ""

# Очистка
cd /
rm -rf /tmp/testptp_build

echo "✅ Настройка завершена!"