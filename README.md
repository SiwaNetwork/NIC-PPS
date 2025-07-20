# Intel NIC PPS Configuration and Monitoring Tool

Комплексное решение для конфигурации и мониторинга сетевых карт Intel с поддержкой PPS (Pulse Per Second) и TCXO (Temperature Compensated Crystal Oscillator).

**🆕 НОВОЕ: Поддержка TimeNIC (Intel I226 NIC, SMA, TCXO)**
- Генерация 1 Гц (PPS) через SDP0 → SMA1
- Приём внешнего PPS через SDP1 → SMA2  
- Синхронизация PHC по внешнему сигналу
- Поддержка PTM (PCIe Time Management)
- Интеграция с linuxptp, testptp, ts2phc

## 🚀 Возможности

- **GUI интерфейс**: Графический интерфейс для удобной настройки
- **CLI интерфейс**: Командная строка для автоматизации и скриптов
- **WEB интерфейс**: Веб-приложение для удаленного управления
- **PPS поддержка**: Настройка и мониторинг PPS сигналов
- **PTP поддержка**: Интеграция с linuxptp и testptp для точной синхронизации времени
- **TCXO поддержка**: Работа с температурно-компенсированными кварцевыми генераторами
- **Мониторинг состояния**: Отслеживание производительности и состояния карт
- **Многоплатформенность**: Поддержка различных Linux дистрибутивов

## 📋 Поддерживаемые драйверы

- **IGB**: Intel Gigabit Ethernet
- **I40E**: Intel 40 Gigabit Ethernet  
- **IXGBE**: Intel 10 Gigabit Ethernet
- **🆕 IGC**: Intel I226 TimeNIC (с поддержкой PPS, SMA, TCXO)

## 🛠 Установка

### Требования
- Python 3.8+
- Linux система с поддержкой sysfs
- Права root для изменения настроек NIC карт

### Быстрая установка
```bash
# Клонирование репозитория
git clone https://github.com/your-repo/intel-nic-pps-tool.git
cd intel-nic-pps-tool

# Установка зависимостей
pip install -r requirements.txt

# Проверка установки
python run.py --check
```

Подробные инструкции по установке см. в [INSTALL.md](INSTALL.md).

## 🎯 Использование

### GUI интерфейс
```bash
python run.py --gui
```

**Возможности GUI:**
- Таблица со всеми обнаруженными NIC картами
- Настройка PPS режимов (отключен, входной, выходной, оба)
- Управление TCXO
- Мониторинг в реальном времени с графиками
- Сохранение и загрузка конфигураций

### CLI интерфейс

#### Обычные NIC карты
```bash
# Список всех NIC карт
python run.py --cli list-nics

# Информация о конкретной карте
python run.py --cli info eth0

# Настройка PPS режима
python run.py --cli set-pps eth0 --mode input

# Настройка PPS с PTP поддержкой
python run.py --cli set-pps-ptp eth0 --mode input --ptp-device /dev/ptp0

# Настройка TCXO
python run.py --cli set-tcxo eth0 --enable

# Мониторинг карты
python run.py --cli monitor eth0 --interval 1

# Мониторинг PTP синхронизации
python run.py --cli monitor-ptp eth0 --interval 1

# Комплексный мониторинг
python run.py --cli monitor-all --ptp --pps --temperature --interval 1

# Список PTP устройств
python run.py --cli list-ptp

# Общий статус
python run.py --cli status

# Управление конфигурацией
python run.py --cli config --output config.json
python run.py --cli config --config config.json
```

#### TimeNIC карты (Intel I226, SMA, TCXO)
```bash
# Список всех TimeNIC карт
python run.py --cli timenic list-timenics

# Информация о TimeNIC карте
python run.py --cli timenic info eth0

# Настройка PPS режима (SMA1/SMA2)
python run.py --cli timenic set-pps eth0 --mode output  # SMA1 выход
python run.py --cli timenic set-pps eth0 --mode input   # SMA2 вход
python run.py --cli timenic set-pps eth0 --mode both    # Оба режима

# Управление TCXO
python run.py --cli timenic set-tcxo eth0 --enable

# Запуск синхронизации PHC по внешнему PPS
python run.py --cli timenic start-phc-sync eth0

# Включение PTM (PCIe Time Management)
python run.py --cli timenic enable-ptm eth0

# Список PTP устройств
python run.py --cli timenic list-ptp

# Мониторинг TimeNIC карты
python run.py --cli timenic monitor eth0 --interval 1

# Установка драйвера TimeNIC с патчем
python run.py --cli timenic install-driver

# Создание systemd сервиса для автозапуска
python run.py --cli timenic create-service

# Чтение PPS событий
python run.py --cli timenic read-pps /dev/ptp0 --count 5

# Установка периода PPS сигнала
python run.py --cli timenic set-period /dev/ptp0 --period 1000000000

# Общий статус TimeNIC системы
python run.py --cli timenic status

# Сохранение конфигурации
python run.py --cli timenic config --output timenic_config.json
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
- Загрузка и сохранение конфигураций

## 📊 Мониторинг

### Режимы PPS
- **disabled**: PPS отключен
- **input**: Входной PPS сигнал
- **output**: Выходной PPS сигнал
- **both**: Оба режима одновременно

### TimeNIC специфичные возможности
- **SMA1 (SDP0)**: Выход PPS сигнала (1 Гц)
- **SMA2 (SDP1)**: Вход внешнего PPS сигнала
- **PHC синхронизация**: Коррекция времени по внешнему PPS
- **PTM поддержка**: PCIe Time Management (если поддерживается CPU)
- **TCXO управление**: Температурно-компенсированный кварцевый генератор

### Метрики мониторинга
- **Трафик**: RX/TX байты, пакеты, ошибки
- **Температура**: Мониторинг температуры карт
- **Статус**: Состояние интерфейсов (up/down)
- **Производительность**: Скорость передачи данных
- **PTP информация**: PHC offset, frequency, PPS события
- **SMA статус**: Состояние SMA разъемов

## 🔧 Конфигурация

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

### API документация

#### REST API
```bash
# Получение списка NIC карт
GET /api/nics

# Получение информации о карте
GET /api/nics/{interface}

# Установка PPS режима
POST /api/nics/{interface}/pps
{
    "mode": "input|output|both|disabled"
}

# Установка TCXO
POST /api/nics/{interface}/tcxo
{
    "enabled": true|false
}
```

#### WebSocket события
```javascript
const socket = io();
socket.on('monitoring_data', function(data) {
    console.log('Данные мониторинга:', data);
});
```

## 🏗 Архитектура

```
intel-nic-pps-tool/
├── core/                 # Основная логика
│   ├── __init__.py
│   └── nic_manager.py    # Менеджер NIC карт
├── gui/                  # GUI приложение (PyQt6)
│   ├── __init__.py
│   └── main.py          # PyQt6 интерфейс
├── cli/                  # CLI интерфейс (Click)
│   ├── __init__.py
│   └── main.py          # Click интерфейс
├── web/                  # WEB приложение (Flask)
│   ├── __init__.py
│   ├── app.py           # Flask приложение
│   ├── templates/       # HTML шаблоны
│   └── static/          # Статические файлы
├── drivers/              # Драйверы Intel NIC
│   ├── __init__.py
│   └── intel_driver.py  # Драйверы для IGB, I40E, IXGBE
├── tests/                # Тесты
│   ├── __init__.py
│   └── test_nic_manager.py
├── docs/                 # Документация
├── examples/             # Примеры конфигураций
├── run.py               # Главный скрипт запуска
├── requirements.txt     # Зависимости Python
└── README.md           # Документация
```

## 🧪 Тестирование

```bash
# Запуск всех тестов
python -m pytest tests/

# Линтинг кода
flake8 core/ gui/ cli/ web/ drivers/
black core/ gui/ cli/ web/ drivers/

# Типизация
mypy core/ gui/ cli/ web/ drivers/
```

## 🔍 Устранение неполадок

### Проблемы с правами доступа
```bash
# Проверка прав на sysfs
ls -la /sys/class/net/eth0/device/

# Установка прав (требуются root права)
sudo chmod 666 /sys/class/net/eth0/device/tcxo_enabled
```

### Проблемы с драйверами
```bash
# Проверка загруженных драйверов
lsmod | grep -E "(igb|i40e|ixgbe)"

# Перезагрузка драйвера
sudo rmmod igb
sudo modprobe igb
```

### Проблемы с PPS
```bash
# Проверка поддержки PPS
ethtool -T eth0

# Проверка sysfs файлов
ls -la /sys/class/net/eth0/pps*
```

## 📚 Документация

- [Инструкции по установке](INSTALL.md)
- [Ubuntu 24.04 Setup Guide](docs/UBUNTU_24_04_SETUP.md)
- [🆕 TimeNIC Setup Guide](docs/TIMENIC_SETUP.md)
- [API документация](docs/README.md)
- [Примеры конфигураций](examples/)

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для подробностей.

## 🆘 Поддержка

Для получения поддержки:
1. Проверьте документацию
2. Изучите логи приложения
3. Создайте issue в репозитории проекта

## 📈 История версий

### v1.0.0
- Первоначальный релиз
- Поддержка GUI, CLI и WEB интерфейсов
- Поддержка PPS и TCXO
- Мониторинг в реальном времени
- Поддержка драйверов IGB, I40E, IXGBE

---

**Разработано с ❤️ для сообщества Intel NIC пользователей**