# 🧾 Настройка TimeNIC (Intel I226 NIC, SMA, TCXO) на Ubuntu 24.04

## ⚙️ Цель

Настроить **сетевую карту PCIe TimeNIC** с Intel I226 NIC, TCXO-осциллятором и SMA-разъёмами для:
- **Генерации 1 Гц (PPS)** через SDP0 → SMA1
- **Приёма внешнего PPS** через SDP1 → SMA2
- **Синхронизации PHC** по внешнему сигналу
- **Использования PTM (PCIe Time Management)** если поддерживается CPU
- **Работы с linuxptp**, `testptp`, `ts2phc` и другими утилитами

## 🔧 Этап 1: Подготовка системы

### Установка зависимостей

```bash
sudo apt update
sudo apt install -y openssh-server net-tools gcc vim dkms linuxptp \
    linux-headers-$(uname -r) libgpiod-dev pkg-config build-essential git
```

### Установка Python зависимостей

```bash
pip install -r requirements.txt
```

## 💻 Этап 2: Сборка и установка testptp

```bash
cd ~
mkdir testptp && cd testptp

# Загрузка исходников
wget https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/tools/testing/selftests/ptp/testptp.c
wget https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/include/uapi/linux/ptp_clock.h
sudo cp ptp_clock.h /usr/include/linux/

# Компиляция
gcc -Wall -lrt testptp.c -o testptp

# Установка
sudo cp testptp /usr/bin/
```

## 🧪 Этап 3: Проверка PTP-устройства

```bash
# Проверка PTP устройства
ethtool -T enp3s0

# Ожидаемый вывод:
# PTP Hardware Clock: 0
# → Это означает, что устройство доступно как /dev/ptp0
```

## 🔧 Этап 4: Установка драйвера TimeNIC с патчем

### Автоматическая установка через CLI

```bash
python run.py --cli timenic install-driver
```

### Ручная установка

```bash
cd ~
wget https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip
unzip intel-igc-ppsfix_ubuntu.zip
cd intel-igc-ppsfix

# Удаление старого драйвера
sudo dkms remove igc -v 5.4.0-7642.46

# Добавление и сборка нового драйвера
sudo dkms add .
sudo dkms build --force igc -v 5.4.0-7642.46
sudo dkms install --force igc -v 5.4.0-7642.46

# Замена оригинального модуля
sudo cp /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst \
        /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst.bak

sudo cp /lib/modules/$(uname -r)/updates/dkms/igc.ko.zst \
        /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/

# Обновление initramfs и перезагрузка
sudo depmod -a
sudo update-initramfs -u
sudo reboot
```

### Проверка после перезагрузки

```bash
# Проверка драйвера
modinfo igc | grep filename
ethtool -i enp1s0

# Проверка TimeNIC карт
python run.py --cli timenic list-timenics
```

## 🎯 Этап 5: Настройка PPS через CLI

### Включение PPS-выхода на SMA1 (SDP0)

```bash
# Назначение SDP0 как выходного пина
python run.py --cli timenic set-pps eth0 --mode output

# Или вручную:
sudo testptp -d /dev/ptp0 -L0,2
sudo testptp -d /dev/ptp0 -p 1000000000
```

### Включение PPS-входа на SMA2 (SDP1)

```bash
# Назначение SDP1 как входного пина
python run.py --cli timenic set-pps eth0 --mode input

# Или вручную:
sudo testptp -d /dev/ptp0 -L1,1
```

### Включение обоих режимов

```bash
python run.py --cli timenic set-pps eth0 --mode both
```

## 📥 Этап 6: Чтение внешнего PPS-сигнала

```bash
# Чтение 5 событий
python run.py --cli timenic read-pps /dev/ptp0 --count 5

# Или вручную:
sudo testptp -d /dev/ptp0 -e 5
```

## 🔄 Этап 7: Синхронизация PHC по внешнему PPS

### Запуск синхронизации

```bash
# Автоматический запуск
python run.py --cli timenic start-phc-sync eth0

# Или вручную:
sudo phc_ctl enp1s0 "set;" adj 37
sudo ts2phc -c /dev/ptp0 -s generic --ts2phc.pin_index 1 -m -l 7
```

### Ожидаемые логи

```
rms < 50 ns
freq ±1e5 ppb
delay 0+/-0
```

## 🧰 Этап 8: Использование только восходящего фронта PPS

Если вы видите два события на один импульс, это означает, что драйвер читает оба фронта сигнала. 

### Автоматическое исправление

Используйте предоставленный патч драйвера igc:

```bash
# Применение патча (требует root)
sudo /home/shiwa-time/NIC-PPS/scripts/apply_igc_patch.sh

# Тестирование результата
python scripts/diagnose_pps_edges.py
```

### Ручное исправление

Если автоматический скрипт не работает:

1. Отредактируйте файл драйвера `drivers/net/ethernet/intel/igc/igc_ptp.c`
2. Найдите строку `cfg.extts.flags = RISING_EDGE;`
3. Пересоберите драйвер и перезагрузитесь

### Что делает патч

- **Принудительное использование восходящего фронта**: Все PPS события настраиваются только на восходящий фронт
- **Фильтрация на уровне драйвера**: Проверка уровня пина после прерывания для исключения ложных событий
- **Отслеживание конфигурации**: Сохранение настроек пинов и флагов для корректной обработки

Подробное описание патча см. в [DRIVER_PATCH_GUIDE.md](DRIVER_PATCH_GUIDE.md)

## 🛠 Этап 9: Автозапуск при загрузке

### Создание systemd сервиса

```bash
python run.py --cli timenic create-service
```

### Ручное создание

```bash
sudo nano /etc/systemd/system/ptp-nic-setup.service
```

Содержимое файла:

```ini
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
```

Активация:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ptp-nic-setup
sudo systemctl start ptp-nic-setup
```

## 🧪 Этап 10: Проверка работоспособности

### Проверка PPS

```bash
# Проверка текущих значений PPS
cat /sys/class/timecard/ocp0/pps/assert

# Использование ppstest
sudo apt install pps-tools
sudo ppstest /dev/pps0
```

### Проверка синхронизации PHC

```bash
# Проверка состояния синхронизации PHC
sudo phc_ctl /dev/ptp0 get

# Проверка работы ts2phc
journalctl -u ptp4l
```

## 🧩 Этап 11: Использование PTM (PCIe Time Management)

### Проверка поддержки PTM

```bash
# Список поддерживаемых процессоров:
# https://www.opencompute.org/wiki/PTM_Readiness

# Проверка активации PTM
lspci -vvv

# Ищите строку:
# Capabilities: [44] Precision Time Measurement
```

### Включение PTM

```bash
# Автоматическое включение
python run.py --cli timenic enable-ptm eth0

# Или вручную:
echo 1 > /sys/bus/pci/devices/0000:XX:YY.Z/enable_ptm
# (замените XX:YY.Z на свой PCI-адрес)
```

## 🧪 Этап 12: Мониторинг и диагностика

### Мониторинг в реальном времени

```bash
# Мониторинг TimeNIC карты
python run.py --cli timenic monitor eth0 --interval 1

# Общий статус системы
python run.py --cli timenic status
```

### Полезные команды

| Задача | Команда |
|--------|----------|
| Проверить PTP-устройства | `ethtool -T enp1s0` |
| Включить 1 Гц на SMA1 | `python run.py --cli timenic set-pps eth0 --mode output` |
| Включить PPS-вход на SMA2 | `python run.py --cli timenic set-pps eth0 --mode input` |
| Синхронизировать PHC | `python run.py --cli timenic start-phc-sync eth0` |
| Проверить драйвер | `modinfo igc \| grep filename` |
| Проверить PPS | `sudo ppstest /dev/pps0` |
| Логи синхронизации | `journalctl -u ptp4l` |

## 📦 Альтернатива: Использование ptp_ocp (если есть FPGA)

Если вы работаете с TimeCard или аналогичным устройством с драйвером `ptp_ocp`:

```bash
# Генерация 1 Гц через GEN1
echo 1000000000 > /sys/class/timecard/ocp0/gen1/signal
echo 1 > /sys/class/timecard/ocp0/gen1/running
echo out:GEN1 > /sys/class/timecard/ocp0/sma1

# Приём PPS через SMA2
echo in:PPS1 > /sys/class/timecard/ocp0/sma2
```

## 🧩 Что дальше?

Если вы хотите:
- Интеграция с GNSS/MAC/IRIG-B
- Python-скрипт мониторинга PPS и частоты
- Автоматическое восстановление после потери сигнала
- Готовый образ Ubuntu с преднастроенными драйверами
- Работу с `ptp4l`, `phc2sys`, `chrony`, `timemaster`

— используйте CLI команды TimeNIC для создания **рабочего окружения с микросекундной точностью**.

## 🔗 Полезные ссылки

- [TimeNIC GitHub](https://github.com/Time-Appliances-Project/Products/tree/main/TimeNIC)
- [PTM Readiness List](https://www.opencompute.org/wiki/PTM_Readiness)
- [Видео про PTM от Кевина Стэнтона](https://www.youtube.com/watch?v=JOucm1vjk8o)
- [OCP TAP Wiki](https://www.opencompute.org/wiki/Time_Appliances_Project)

## 📌 Заключение

Вы успешно настроили TimeNIC PCIe (Intel I226 NIC, TCXO, SMA):
- ✔️ Выдача 1 Гц через SMA1
- ✔️ Приём внешнего PPS через SMA2
- ✔️ Коррекция PHC по внешнему PPS
- ✔️ Поддержка PTM (при наличии аппаратной поддержки)

Теперь используйте CLI команды для управления и мониторинга:

```bash
# Список TimeNIC карт
python run.py --cli timenic list-timenics

# Информация о карте
python run.py --cli timenic info eth0

# Настройка PPS
python run.py --cli timenic set-pps eth0 --mode both

# Мониторинг
python run.py --cli timenic monitor eth0 --interval 1
```