# Инструкции по установке

## Требования к системе

### Операционная система
- Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- Поддержка sysfs
- Права root для изменения настроек NIC карт

### Аппаратные требования
- Intel сетевые карты с поддержкой PPS
- Поддерживаемые драйверы: IGB, I40E, IXGBE

### Программные требования
- Python 3.8+
- pip (менеджер пакетов Python)
- ethtool (для работы с PPS)

## Установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/your-repo/intel-nic-pps-tool.git
cd intel-nic-pps-tool
```

### 2. Установка зависимостей Python
```bash
# Установка системных зависимостей
sudo apt-get update
sudo apt-get install python3-pip python3-venv

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка Python зависимостей
pip install -r requirements.txt
```

### 3. Установка системных утилит
```bash
# Ubuntu/Debian
sudo apt-get install ethtool

# CentOS/RHEL
sudo yum install ethtool

# Arch Linux
sudo pacman -S ethtool
```

### 4. Проверка установки
```bash
# Проверка системы
python run.py --check

# Тест CLI
python run.py --cli list-nics

# Тест GUI
python run.py --gui

# Тест WEB
python run.py --web
```

## Настройка прав доступа

### Автоматическая настройка
```bash
# Создание udev правил для автоматического изменения прав
sudo tee /etc/udev/rules.d/99-intel-nic.rules > /dev/null << EOF
# Правила для Intel NIC карт
SUBSYSTEM=="net", KERNEL=="eth*", ATTR{device/driver}=="*igb*", MODE="0666"
SUBSYSTEM=="net", KERNEL=="eth*", ATTR{device/driver}=="*i40e*", MODE="0666"
SUBSYSTEM=="net", KERNEL=="eth*", ATTR{device/driver}=="*ixgbe*", MODE="0666"
EOF

# Перезагрузка udev правил
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Ручная настройка
```bash
# Для каждой Intel NIC карты
sudo chmod 666 /sys/class/net/eth0/device/tcxo_enabled
sudo chmod 666 /sys/class/net/eth0/pps_input
sudo chmod 666 /sys/class/net/eth0/pps_output
```

## Проверка драйверов

### Проверка загруженных драйверов
```bash
# Проверка Intel драйверов
lsmod | grep -E "(igb|i40e|ixgbe)"

# Если драйверы не загружены
sudo modprobe igb
sudo modprobe i40e
sudo modprobe ixgbe
```

### Проверка поддержки PPS
```bash
# Проверка ethtool
ethtool --version

# Проверка PPS поддержки для конкретной карты
ethtool -T eth0
```

## Устранение неполадок

### Проблема: "Intel NIC карты не обнаружены"
```bash
# Проверка сетевых интерфейсов
ip link show

# Проверка драйверов
ls -la /sys/class/net/*/device/driver

# Проверка производителя
lspci | grep -i ethernet
```

### Проблема: "Нет прав доступа"
```bash
# Проверка прав
ls -la /sys/class/net/eth0/device/

# Установка прав
sudo chmod 666 /sys/class/net/eth0/device/tcxo_enabled
```

### Проблема: "ethtool не найден"
```bash
# Установка ethtool
sudo apt-get install ethtool  # Ubuntu/Debian
sudo yum install ethtool      # CentOS/RHEL
```

### Проблема: "Ошибка импорта модулей"
```bash
# Проверка Python окружения
python --version
pip list

# Переустановка зависимостей
pip install --upgrade -r requirements.txt
```

## Настройка автозапуска

### Создание systemd сервиса
```bash
sudo tee /etc/systemd/system/intel-nic-pps.service > /dev/null << EOF
[Unit]
Description=Intel NIC PPS Configuration and Monitoring Tool
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/intel-nic-pps-tool
ExecStart=/path/to/intel-nic-pps-tool/venv/bin/python run.py --web
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Включение автозапуска
sudo systemctl enable intel-nic-pps.service
sudo systemctl start intel-nic-pps.service
```

### Проверка статуса сервиса
```bash
sudo systemctl status intel-nic-pps.service
sudo journalctl -u intel-nic-pps.service -f
```

## Обновление

### Обновление кода
```bash
git pull origin main
pip install --upgrade -r requirements.txt
```

### Обновление конфигурации
```bash
# Создание резервной копии
cp config.json config.json.backup

# Применение новой конфигурации
python run.py --cli config --config config.json
```

## Удаление

### Удаление сервиса
```bash
sudo systemctl stop intel-nic-pps.service
sudo systemctl disable intel-nic-pps.service
sudo rm /etc/systemd/system/intel-nic-pps.service
```

### Удаление udev правил
```bash
sudo rm /etc/udev/rules.d/99-intel-nic.rules
sudo udevadm control --reload-rules
```

### Удаление Python окружения
```bash
deactivate  # если виртуальное окружение активно
rm -rf venv/
```

## Поддержка

При возникновении проблем:

1. Проверьте логи: `journalctl -u intel-nic-pps.service`
2. Запустите проверку системы: `python run.py --check`
3. Проверьте документацию в папке `docs/`
4. Создайте issue в репозитории проекта