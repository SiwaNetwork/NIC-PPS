# 🧾 Руководство по настройке TimeNIC

Настройка **сетевой карты PCIe TimeNIC** с Intel I226 NIC, TCXO-осциллятором и SMA-разъёмами на Ubuntu 24.04.

## ⚙️ Цель

- **Генерация 1 Гц (PPS)** через SDP0 → SMA1
- **Приём внешнего PPS** через SDP1 → SMA2
- **Синхронизация PHC** по внешнему сигналу
- **Использование PTM (PCIe Time Management)** если поддерживается CPU
- **Работа с linuxptp**, `testptp`, `ts2phc` и другими утилитами

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
# Системные пакеты
sudo apt update
sudo apt install -y openssh-server net-tools gcc vim dkms linuxptp \
    linux-headers-$(uname -r) libgpiod-dev pkg-config build-essential git

# Python зависимости
pip install -r requirements.txt
```

### 2. Установка testptp

```bash
# Автоматическая установка
sudo bash scripts/install_testptp.sh

# Или ручная установка
cd /tmp
mkdir testptp_build && cd testptp_build
wget https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/tools/testing/selftests/ptp/testptp.c
wget https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/include/uapi/linux/ptp_clock.h
sudo cp ptp_clock.h /usr/include/linux/
gcc -Wall -lrt testptp.c -o testptp
sudo cp testptp /usr/bin/
```

### 3. Проверка системы

```bash
# Проверка TimeNIC карт и PTP устройств
python run.py --check

# Список TimeNIC карт
python run.py --cli timenic list-timenics

# Список PTP устройств
python run.py --cli timenic list-ptp
```

## 📡 Настройка PPS

### Включение PPS выхода на SMA1 (1 Гц)

```bash
# Через CLI
python run.py --cli timenic set-pps enp3s0 --mode output

# Или напрямую через testptp
sudo testptp -d /dev/ptp0 -L0,2
sudo testptp -d /dev/ptp0 -p 1000000000
```

### Включение PPS входа на SMA2

```bash
# Через CLI
python run.py --cli timenic set-pps enp3s0 --mode input

# Или напрямую через testptp
sudo testptp -d /dev/ptp0 -L1,1
```

### Чтение внешних PPS событий

```bash
# Через CLI
python run.py --cli timenic read-pps /dev/ptp0 --count 5

# Или напрямую через testptp
sudo testptp -d /dev/ptp0 -e 5
```

## 🔄 Синхронизация PHC

### Синхронизация с системным временем

```bash
# Через CLI
python run.py --cli timenic sync-phc enp3s0

# Или напрямую через phc_ctl
sudo phc_ctl enp3s0 "set;" adj 37
```

### Синхронизация по внешнему PPS

```bash
# Через CLI
python run.py --cli timenic start-phc-sync enp3s0

# Или напрямую через ts2phc
sudo ts2phc -c /dev/ptp0 -s generic --ts2phc.pin_index 1 -m -l 7
```

## 🔧 Установка драйвера (опционально)

Если стандартный драйвер не поддерживает все функции TimeNIC:

```bash
cd /tmp
wget https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip
unzip intel-igc-ppsfix_ubuntu.zip
cd intel-igc-ppsfix

# Удаление старого драйвера
sudo dkms remove igc -v 5.4.0-7642.46

# Установка нового
sudo dkms add .
sudo dkms build --force igc -v 5.4.0-7642.46
sudo dkms install --force igc -v 5.4.0-7642.46

# Замена модуля ядра
sudo cp /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst \
        /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst.bak

sudo cp /lib/modules/$(uname -r)/updates/dkms/igc.ko.zst \
        /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/

# Обновление и перезагрузка
sudo depmod -a
sudo update-initramfs -u
sudo reboot
```

## 🚀 Автозапуск при загрузке

```bash
# Создание systemd сервиса
sudo python run.py --cli timenic create-service

# Или с включенной синхронизацией PHC
sudo python scripts/create_timenic_service.py --interface enp3s0 --enable-phc-sync

# Управление сервисом
sudo systemctl start ptp-nic-setup
sudo systemctl status ptp-nic-setup
sudo systemctl enable ptp-nic-setup
```

## 📊 Мониторинг

```bash
# Мониторинг TimeNIC в реальном времени
python run.py --cli timenic monitor enp3s0 --interval 1

# Проверка PPS
sudo ppstest /dev/pps0

# Логи синхронизации
sudo journalctl -u ptp-nic-setup -f
```

## 🎯 PTM (PCIe Time Management)

### Проверка поддержки PTM

```bash
# Список поддерживаемых процессоров:
# https://www.opencompute.org/wiki/PTM_Readiness

# Проверка в системе
lspci -vvv | grep "Precision Time Measurement"
```

### Включение PTM

```bash
# Через CLI
python run.py --cli timenic enable-ptm enp3s0

# Или вручную
echo 1 > /sys/bus/pci/devices/0000:XX:YY.Z/enable_ptm
```

## 📋 Полезные команды

| Задача | Команда |
|--------|----------|
| Проверить PTP устройства | `ethtool -T enp3s0` |
| Включить 1 Гц на SMA1 | `python run.py --cli timenic set-pps enp3s0 --mode output` |
| Включить PPS вход на SMA2 | `python run.py --cli timenic set-pps enp3s0 --mode input` |
| Читать PPS события | `python run.py --cli timenic read-pps /dev/ptp0 --count 5` |
| Установить период 10 Гц | `python run.py --cli timenic set-period /dev/ptp0 --period 100000000` |
| Синхронизировать PHC | `python run.py --cli timenic start-phc-sync enp3s0` |
| Проверить драйвер | `modinfo igc | grep filename` |
| Проверить PPS | `sudo ppstest /dev/pps0` |

## 🔍 Диагностика

### Проверка драйвера

```bash
modinfo igc | grep filename
ethtool -i enp3s0
```

### Проверка PTP

```bash
# Информация о PTP
sudo testptp -d /dev/ptp0 -c

# Возможности устройства
sudo testptp -d /dev/ptp0 -C
```

### Проверка SMA портов

```bash
# SMA1 (выход)
cat /sys/class/ptp/ptp0/pins/SDP0

# SMA2 (вход)
cat /sys/class/ptp/ptp0/pins/SDP1
```

## ❓ Решение проблем

### PTP устройство не найдено

1. Проверьте, что драйвер загружен: `lsmod | grep igc`
2. Проверьте dmesg: `dmesg | grep -i ptp`
3. Переустановите драйвер

### PPS события не приходят

1. Проверьте подключение к SMA2
2. Убедитесь, что SDP1 настроен как вход: `sudo testptp -d /dev/ptp0 -L1,1`
3. Проверьте источник PPS сигнала

### Большая ошибка синхронизации

1. Проверьте качество внешнего PPS
2. Увеличьте уровень логов ts2phc: `-l 7`
3. Проверьте температуру карты