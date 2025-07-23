# Intel NIC PPS Configuration and Monitoring Tool

Комплексное решение для конфигурации и мониторинга сетевых карт Intel с поддержкой PPS (Pulse Per Second), TimeNIC и TCXO (Temperature Compensated Crystal Oscillator).

## 🚀 Быстрый старт

### Автоматическая установка драйвера IGC (для карт I225-LM/I225-V)
```bash
sudo ./install_igc_driver.sh
```

### Запуск инструмента
```bash
# GUI интерфейс
python run.py --gui

# WEB интерфейс
python run.py --web

# CLI интерфейс
python run.py --cli list-nics
```

## 📋 Возможности

### Основные функции
- **Обнаружение Intel NIC карт**: Автоматическое обнаружение и идентификация сетевых карт Intel
- **PPS поддержка**: Настройка и мониторинг PPS сигналов (входной, выходной, оба режима)
- **TimeNIC поддержка**: Полная поддержка карт Intel I226 с SMA разъемами
- **TCXO поддержка**: Управление температурно-компенсированными кварцевыми генераторами
- **PTM поддержка**: PCIe Time Management для синхронизации времени
- **Мониторинг производительности**: Отслеживание трафика, температуры и статистики карт
- **Многоплатформенность**: GUI, CLI и WEB интерфейсы

### Поддерживаемые драйверы
- **IGC**: Intel 2.5G Ethernet (I225/I226)
- **IGB**: Intel Gigabit Ethernet
- **I40E**: Intel 40 Gigabit Ethernet  
- **IXGBE**: Intel 10 Gigabit Ethernet

## 🔧 Установка

### Системные требования
- Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- Python 3.8+
- Права root для изменения настроек NIC карт
- Для TimeNIC: linuxptp, testptp, ts2phc, phc_ctl

### Установка зависимостей

#### Ubuntu/Debian
```bash
# Системные пакеты
sudo apt update
sudo apt install -y dkms build-essential linux-headers-$(uname -r) \
    ethtool linuxptp libgpiod-dev pkg-config git

# Python зависимости
pip install -r requirements.txt
```

#### RHEL/CentOS/Fedora
```bash
# Системные пакеты
sudo yum install -y dkms gcc make kernel-devel-$(uname -r) \
    ethtool linuxptp libgpiod-devel pkg-config git

# Python зависимости
pip install -r requirements.txt
```

### Установка драйвера IGC с исправлением PPS

Драйвер необходим для карт Intel I225-LM/I225-V для корректной работы PPS:

```bash
# Автоматическая установка
sudo ./install_igc_driver.sh

# Ручная установка
cd drivers/intel-igc-ppsfix
sudo dkms add -m igc -v 1.0
sudo dkms build -m igc -v 1.0
sudo dkms install -m igc -v 1.0
```

## 💻 Использование

### GUI интерфейс
```bash
python run.py --gui
```

### WEB интерфейс
```bash
python run.py --web
# Откройте http://localhost:5000
```

### CLI интерфейс

#### Обычные NIC команды
```bash
# Список всех NIC карт
python run.py --cli list-nics

# Информация о карте
python run.py --cli info enp3s0

# Установка PPS режима
python run.py --cli set-pps enp3s0 --mode output

# Мониторинг
python run.py --cli monitor enp3s0 --interval 1
```

#### TimeNIC команды
```bash
# Список TimeNIC карт
python run.py --cli timenic list-timenics

# Установка PPS выхода на SMA1 (1 Гц)
python run.py --cli timenic set-pps enp3s0 --mode output

# Установка PPS входа на SMA2
python run.py --cli timenic set-pps enp3s0 --mode input

# Чтение PPS событий
python run.py --cli timenic read-pps /dev/ptp0 --count 5

# Синхронизация PHC по внешнему PPS
python run.py --cli timenic start-phc-sync enp3s0

# Включение PTM
python run.py --cli timenic enable-ptm enp3s0

# Создание systemd сервиса
sudo python run.py --cli timenic create-service
```

## 📁 Структура проекта

```
intel-nic-pps-tool/
├── core/                  # Основные модули
│   ├── nic_manager.py    # Управление NIC картами
│   ├── timenic_manager.py # Управление TimeNIC картами
│   └── pps_config.py     # Конфигурация PPS
├── gui/                   # GUI приложение (PyQt6)
├── cli/                   # CLI приложение (Click)
├── web/                   # WEB приложение (flask)
├── drivers/              # Драйверы
│   └── intel-igc-ppsfix/ # Драйвер IGC с исправлением PPS
├── scripts/              # Вспомогательные скрипты
├── tests/                # Тесты
└── docs/                 # Дополнительная документация
```

## 🔬 TimeNIC настройка

TimeNIC - это специализированные сетевые карты Intel I226 с:
- SMA разъемами для PPS сигналов
- TCXO осциллятором для точного времени
- Поддержкой PTM (PCIe Time Management)

### Быстрая настройка TimeNIC

1. **Генерация PPS на SMA1 (1 Гц)**:
   ```bash
   python run.py --cli timenic set-pps enp3s0 --mode output
   ```

2. **Прием внешнего PPS на SMA2**:
   ```bash
   python run.py --cli timenic set-pps enp3s0 --mode input
   ```

3. **Синхронизация по внешнему PPS**:
   ```bash
   python run.py --cli timenic start-phc-sync enp3s0
   ```

## 📚 Дополнительная документация

- [Подробная документация](docs/README.md)
- [Настройка TimeNIC](docs/TIMENIC_SETUP.md)
- [Настройка Ubuntu 24.04](docs/UBUNTU_24_04_SETUP.md)
- [Изменения в драйвере](TIMENIC_CHANGES.md)
- [Решение проблем с PTP](PTP_SETUP_ISSUE_SOLUTION.md)

## 📝 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 🤝 Вклад в проект

Приветствуются pull requests. Для больших изменений сначала откройте issue для обсуждения.

## ⚠️ Предупреждение

Изменение настроек сетевых карт требует прав администратора и может повлиять на сетевое соединение. Используйте с осторожностью в production окружении.