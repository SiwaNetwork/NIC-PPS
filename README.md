# Intel NIC PPS Configuration and Monitoring Tool

Комплексное решение для конфигурации и мониторинга сетевых карт Intel с поддержкой PPS (Pulse Per Second) и TCXO (Temperature Compensated Crystal Oscillator).

## 🚀 Возможности

- **GUI интерфейс**: Графический интерфейс для удобной настройки
- **CLI интерфейс**: Командная строка для автоматизации и скриптов
- **WEB интерфейс**: Веб-приложение для удаленного управления
- **PPS поддержка**: Настройка и мониторинг PPS сигналов
- **TCXO поддержка**: Работа с температурно-компенсированными кварцевыми генераторами
- **Мониторинг состояния**: Отслеживание производительности и состояния карт
- **Многоплатформенность**: Поддержка различных Linux дистрибутивов

## 📋 Поддерживаемые драйверы

- **IGB**: Intel Gigabit Ethernet
- **I40E**: Intel 40 Gigabit Ethernet  
- **IXGBE**: Intel 10 Gigabit Ethernet

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
```bash
# Список всех NIC карт
python run.py --cli list-nics

# Информация о конкретной карте
python run.py --cli info eth0

# Настройка PPS режима
python run.py --cli set-pps eth0 --mode input

# Настройка TCXO
python run.py --cli set-tcxo eth0 --enable

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
- Загрузка и сохранение конфигураций

## 📊 Мониторинг

### Режимы PPS
- **disabled**: PPS отключен
- **input**: Входной PPS сигнал
- **output**: Выходной PPS сигнал
- **both**: Оба режима одновременно

### Метрики мониторинга
- **Трафик**: RX/TX байты, пакеты, ошибки
- **Температура**: Мониторинг температуры карт
- **Статус**: Состояние интерфейсов (up/down)
- **Производительность**: Скорость передачи данных

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