# SHIWA NIC-PPS Configuration and Monitoring Tool - Подробная документация

## Обзор

Intel NIC PPS Configuration and Monitoring Tool - это комплексное решение для конфигурации и мониторинга сетевых карт Intel с поддержкой PPS (Pulse Per Second), TimeNIC, TCXO (Temperature Compensated Crystal Oscillator) и PHC (PTP Hardware Clock) синхронизации.

## Возможности

### Основные функции
- **Обнаружение Intel NIC карт**: Автоматическое обнаружение и идентификация сетевых карт Intel
- **PPS поддержка**: Настройка и мониторинг PPS сигналов (входной, выходной, оба режима)
- **TCXO поддержка**: Управление температурно-компенсированными кварцевыми генераторами
- **PHC синхронизация**: Взаимная синхронизация между PHC часами (`phc2sys`) и синхронизация по внешнему PPS (`ts2phc`)
- **Мониторинг производительности**: Отслеживание трафика и статистики карт
- **PTP мониторинг**: Мониторинг PTP трафика и статистики
- **Многоплатформенность**: GUI, CLI и WEB интерфейсы

### Поддерживаемые драйверы
- **IGB**: Intel Gigabit Ethernet
- **I40E**: Intel 40 Gigabit Ethernet  
- **IXGBE**: Intel 10 Gigabit Ethernet

## Установка

### Требования
- Python 3.8+
- Linux система с поддержкой sysfs
- Права root для изменения настроек NIC карт
- Установленные утилиты: `ethtool`, `testptp`, `phc_ctl`, `ts2phc`, `phc2sys`

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

### Настройка sudo прав
Для корректной работы PPS и PHC синхронизации необходимо настроить права sudo:

```bash
# Создание файла sudoers для PPS команд
echo 'shiwa-time ALL=(ALL) NOPASSWD: /usr/bin/testptp, /usr/bin/phc_ctl, /usr/bin/ts2phc, /usr/bin/phc2sys' | sudo tee /etc/sudoers.d/shiwa-nic-pps

# Проверка прав
sudo -n testptp -d /dev/ptp0 -l
```

### Проверка установки
```bash
python -c "import core.nic_manager; print('Установка успешна')"
```

## Использование

### Запуск приложения
```bash
# GUI интерфейс
python run.py --gui

# CLI интерфейс
python run.py --cli

# WEB интерфейс
python run.py --web
```

### GUI интерфейс
```bash
python run.py --gui
```

**Возможности GUI:**
- Таблица со всеми обнаруженными NIC картами
- Настройка PPS режимов (отключен, входной, выходной, оба)
- Управление TCXO
- PHC синхронизация (phc2sys и ts2phc)
- Мониторинг в реальном времени с графиками
- PTP мониторинг трафика
- Сохранение и загрузка конфигураций

### CLI интерфейс
```bash
# Список всех NIC карт
python run.py --cli list-nics

# Информация о конкретной карте
python run.py --cli info eth0

# Настройка PPS режима
python run.py --cli set-pps eth0 --mode input

# Настройка TCXO
python run.py --cli set-tcxo eth0 --enable

# PHC синхронизация
python run.py --cli start-phc-sync /dev/ptp0 /dev/ptp1
python run.py --cli stop-phc-sync
python run.py --cli start-ts2phc-sync eth0 /dev/ptp0
python run.py --cli stop-ts2phc-sync
python run.py --cli sync-status

# Мониторинг карты
python run.py --cli monitor eth0 --interval 1

# Общий статус
python run.py --cli status

# Управление конфигурацией
python run.py --cli config --output config.json
python run.py --cli config --config config.json
```

### WEB интерфейс
```bash
python run.py --web
```

Откройте браузер и перейдите по адресу: `http://localhost:5000`

**Возможности WEB интерфейса:**
- Современный веб-интерфейс с Bootstrap
- WebSocket для реального времени
- Интерактивные графики с Chart.js
- REST API для интеграции
- PHC синхронизация через веб-интерфейс
- PTP мониторинг
- Загрузка и сохранение конфигураций

## API документация

### REST API (WEB интерфейс)

#### Получение списка NIC карт
```
GET /api/nics
```

#### Получение информации о NIC карте
```
GET /api/nics/{interface}
```

#### Установка PPS режима
```
POST /api/nics/{interface}/pps
Content-Type: application/json

{
    "mode": "input|output|both|disabled"
}
```

#### Установка TCXO
```
POST /api/nics/{interface}/tcxo
Content-Type: application/json

{
    "enabled": true|false
}
```

#### PHC синхронизация
```
POST /api/sync/phc/start
Content-Type: application/json

{
    "source_ptp": "/dev/ptp0",
    "target_ptp": "/dev/ptp1"
}

POST /api/sync/phc/stop

POST /api/sync/ts2phc/start
Content-Type: application/json

{
    "interface": "eth0",
    "ptp_device": "/dev/ptp0"
}

POST /api/sync/ts2phc/stop

GET /api/sync/status
```

#### Управление конфигурацией
```
GET /api/config  # Получение текущей конфигурации
POST /api/config # Применение конфигурации
```

#### Мониторинг
```
POST /api/monitoring/start
Content-Type: application/json

{
    "interface": "eth0"
}

POST /api/monitoring/stop
```

### WebSocket события

#### Подключение
```javascript
const socket = io();
```

#### Получение данных мониторинга
```javascript
socket.on('stats', function(data) {
    console.log('Статистика сети:', data);
});

socket.on('ptp_stats', function(data) {
    console.log('PTP статистика:', data);
});
```

## Конфигурация

### Формат файла конфигурации
```json
[
    {
        "interface": "eth0",
        "pps_mode": "input",
        "tcxo_enabled": true
    },
    {
        "interface": "eth1", 
        "pps_mode": "both",
        "tcxo_enabled": false
    }
]
```

### Переменные окружения
- `INTEL_NIC_DEBUG`: Включить отладочный режим
- `INTEL_NIC_LOG_LEVEL`: Уровень логирования (DEBUG, INFO, WARNING, ERROR)

## Архитектура

### Структура проекта
```
SHIWA NIC-PPS/
├── core/                 # Основная логика
│   ├── __init__.py
│   ├── nic_manager.py    # Менеджер NIC карт
│   └── timenic_manager.py # Менеджер TimeNIC
├── gui/                  # GUI приложение
│   ├── __init__.py
│   └── main.py          # PyQt6 интерфейс
├── cli/                  # CLI интерфейс
│   ├── __init__.py
│   ├── main.py          # Click интерфейс
│   └── timenic_cli.py   # TimeNIC CLI
├── web/                  # WEB приложение
│   ├── __init__.py
│   ├── app.py           # flask приложение
│   ├── templates/       # HTML шаблоны
│   └── static/          # Статические файлы
├── drivers/              # Драйверы
│   ├── __init__.py
│   └── intel_driver.py  # Драйверы Intel NIC
├── tests/                # Тесты
│   ├── __init__.py
│   └── test_nic_manager.py
└── docs/                 # Документация
```

### Основные классы

#### IntelNICManager
Основной класс для работы с NIC картами:
- `get_all_nics()`: Получение списка всех карт
- `get_nic_by_name(name)`: Получение карты по имени
- `set_pps_mode(interface, mode)`: Установка PPS режима
- `set_tcxo_enabled(interface, enabled)`: Управление TCXO
- `get_statistics(interface)`: Получение статистики
- `get_ptp_statistics(interface)`: Получение PTP статистики
- `start_phc_sync(source_ptp, target_ptp)`: Запуск PHC синхронизации
- `stop_phc_sync()`: Остановка PHC синхронизации
- `start_ts2phc_sync(interface, ptp_device)`: Запуск ts2phc синхронизации
- `stop_ts2phc_sync()`: Остановка ts2phc синхронизации
- `get_sync_status()`: Получение статуса синхронизации

#### PPSMode
Перечисление режимов PPS:
- `DISABLED`: Отключен
- `INPUT`: Входной
- `OUTPUT`: Выходной  
- `BOTH`: Оба режима

#### NICInfo
Структура данных для информации о NIC карте:
- `name`: Имя интерфейса
- `mac_address`: MAC адрес
- `ip_address`: IP адрес
- `status`: Статус (up/down)
- `speed`: Скорость
- `duplex`: Режим дуплекса
- `pps_mode`: Режим PPS
- `tcxo_enabled`: Статус TCXO

## Разработка

### Запуск тестов
```bash
python -m pytest tests/
```

### Линтинг кода
```bash
flake8 core/ gui/ cli/ web/ drivers/
black core/ gui/ cli/ web/ drivers/
```

### Типизация
```bash
mypy core/ gui/ cli/ web/ drivers/
```

## Устранение неполадок

### Проблемы с правами доступа
```bash
# Проверка прав на sysfs
ls -la /sys/class/net/eth0/device/

# Проверка sudo прав для PPS команд
sudo -n testptp -d /dev/ptp0 -l
```

### Проблемы с PPS
```bash
# Проверка поддержки PPS
ethtool -T eth0

# Проверка текущего состояния PPS
sudo testptp -d /dev/ptp0 -l

# Ручное управление PPS
sudo testptp -d /dev/ptp0 -L0,2  # Включить выходной PPS
sudo testptp -d /dev/ptp0 -p 1000000000  # Установить период 1 Гц
sudo testptp -d /dev/ptp0 -L0,0  # Отключить выходной PPS
```

### Проблемы с PHC синхронизацией
```bash
# Проверка доступных PTP устройств
ls /dev/ptp*

# Проверка процессов синхронизации
ps aux | grep -E "(phc2sys|ts2phc)"

# Ручная синхронизация
sudo phc2sys -s /dev/ptp0 -c /dev/ptp1 -O 0 -R 16 -m
sudo ts2phc -s /dev/ptp0 -c CLOCK_REALTIME -d 1
```

### Проблемы с драйверами
```bash
# Проверка загруженных драйверов
lsmod | grep -E "(igb|i40e|ixgbe)"

# Перезагрузка драйвера
sudo rmmod igb
sudo modprobe igb
```

## Лицензия

MIT License - см. файл LICENSE для подробностей.

## Поддержка

Для получения поддержки:
1. Проверьте документацию
2. Изучите логи приложения
3. Создайте issue в репозитории проекта

## Вклад в проект

1. Fork репозитория
2. Создайте feature branch
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## История версий

### v1.1.0
- Добавлена PHC синхронизация (phc2sys и ts2phc)
- Исправлен PPS контроль через testptp
- Удален мониторинг температуры
- Добавлен PTP мониторинг трафика
- Улучшена производительность веб-интерфейса
- Добавлены новые CLI команды для синхронизации

### v1.0.0
- Первоначальный релиз
- Поддержка GUI, CLI и WEB интерфейсов
- Поддержка PPS и TCXO
- Мониторинг в реальном времени
- Поддержка драйверов IGB, I40E, IXGBE