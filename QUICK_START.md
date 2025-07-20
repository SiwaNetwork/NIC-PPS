# 🚀 Быстрый старт: TimeNIC (Intel I226 NIC, SMA, TCXO)

## Установка и настройка

### 1. Автоматическая установка
```bash
# Клонирование репозитория
git clone <repository-url>
cd intel-nic-pps-tool

# Автоматическая настройка TimeNIC
sudo ./scripts/setup_timenic.sh
```

### 2. Ручная установка
```bash
# Установка зависимостей
sudo apt update
sudo apt install -y openssh-server net-tools gcc vim dkms linuxptp \
    linux-headers-$(uname -r) libgpiod-dev pkg-config build-essential git

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Сборка testptp
cd /tmp
mkdir testptp && cd testptp
wget https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/tools/testing/selftests/ptp/testptp.c
wget https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/include/uapi/linux/ptp_clock.h
sudo cp ptp_clock.h /usr/include/linux/
gcc -Wall -lrt testptp.c -o testptp
sudo cp testptp /usr/bin/
```

## Основные команды

### Проверка системы
```bash
# Проверка TimeNIC карт
python run.py --cli timenic list-timenics

# Статус системы
python run.py --cli timenic status

# Информация о карте
python run.py --cli timenic info eth0
```

### Настройка PPS

#### Генерация 1 Гц через SMA1 (SDP0)
```bash
python run.py --cli timenic set-pps eth0 --mode output
```

#### Приём внешнего PPS через SMA2 (SDP1)
```bash
python run.py --cli timenic set-pps eth0 --mode input
```

#### Оба режима одновременно
```bash
python run.py --cli timenic set-pps eth0 --mode both
```

### Синхронизация PHC
```bash
# Запуск синхронизации PHC по внешнему PPS
python run.py --cli timenic start-phc-sync eth0
```

### Мониторинг
```bash
# Мониторинг в реальном времени
python run.py --cli timenic monitor eth0 --interval 1

# Чтение PPS событий
python run.py --cli timenic read-pps /dev/ptp0 --count 5
```

### Управление TCXO и PTM
```bash
# Включение TCXO
python run.py --cli timenic set-tcxo eth0 --enable

# Включение PTM (если поддерживается CPU)
python run.py --cli timenic enable-ptm eth0
```

## Полезные команды

### Установка драйвера
```bash
python run.py --cli timenic install-driver
```

### Создание systemd сервиса
```bash
python run.py --cli timenic create-service
```

### Список PTP устройств
```bash
python run.py --cli timenic list-ptp
```

### Установка периода PPS
```bash
python run.py --cli timenic set-period /dev/ptp0 --period 1000000000
```

### Сохранение конфигурации
```bash
python run.py --cli timenic config --output timenic_config.json
```

## Примеры использования

### Полная настройка TimeNIC
```bash
# 1. Проверка карт
python run.py --cli timenic list-timenics

# 2. Настройка PPS (оба режима)
python run.py --cli timenic set-pps eth0 --mode both

# 3. Включение TCXO
python run.py --cli timenic set-tcxo eth0 --enable

# 4. Запуск синхронизации PHC
python run.py --cli timenic start-phc-sync eth0

# 5. Мониторинг
python run.py --cli timenic monitor eth0 --interval 1
```

### Диагностика проблем
```bash
# Проверка статуса системы
python run.py --cli timenic status

# Проверка PTP устройств
python run.py --cli timenic list-ptp

# Чтение PPS событий
python run.py --cli timenic read-pps /dev/ptp0 --count 10
```

## Документация

- [Подробная настройка TimeNIC](docs/TIMENIC_SETUP.md)
- [Инструкции по установке](INSTALL.md)
- [Описание изменений](TIMENIC_CHANGES.md)
- [Примеры конфигураций](examples/)

## Поддержка

При проблемах:
1. Проверьте статус: `python run.py --cli timenic status`
2. Проверьте драйвер: `modinfo igc | grep filename`
3. Проверьте PTP устройства: `ls /dev/ptp*`
4. Проверьте утилиты: `which testptp ts2phc phc_ctl`
5. Изучите документацию в папке `docs/`