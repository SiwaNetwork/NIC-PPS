# Intel NIC PPS Configuration and Monitoring Tool - Документация

## Обзор

Intel NIC PPS Configuration and Monitoring Tool - это комплексное решение для конфигурации и мониторинга сетевых карт Intel с поддержкой PPS (Pulse Per Second) и TCXO (Temperature Compensated Crystal Oscillator).

## Возможности

### Основные функции
- **Обнаружение Intel NIC карт**: Автоматическое обнаружение и идентификация сетевых карт Intel
- **PPS поддержка**: Настройка и мониторинг PPS сигналов (входной, выходной, оба режима)
- **TCXO поддержка**: Управление температурно-компенсированными кварцевыми генераторами
- **Мониторинг производительности**: Отслеживание трафика, температуры и статистики карт
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

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### Проверка установки
```bash
python -c "import core.nic_manager; print('Установка успешна')"
```

## Использование

### GUI интерфейс
```bash
python gui/main.py
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
python cli/main.py list-nics

# Информация о конкретной карте
python cli/main.py info eth0

# Настройка PPS режима
python cli/main.py set-pps eth0 --mode input

# Настройка TCXO
python cli/main.py set-tcxo eth0 --enable

# Мониторинг карты
python cli/main.py monitor eth0 --interval 1

# Общий статус
python cli/main.py status

# Управление конфигурацией
python cli/main.py config --output config.json
python cli/main.py config --config config.json
```

### WEB интерфейс
```bash
python web/app.py
```

Откройте браузер и перейдите по адресу: `http://localhost:5000`

**Возможности WEB интерфейса:**
- Современный веб-интерфейс с Bootstrap
- WebSocket для реального времени
- Интерактивные графики с Chart.js
- REST API для интеграции
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
    "interfaces": ["eth0", "eth1"]
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
socket.on('monitoring_data', function(data) {
    console.log('Данные мониторинга:', data);
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
intel-nic-pps-tool/
├── core/                 # Основная логика
│   ├── __init__.py
│   └── nic_manager.py    # Менеджер NIC карт
├── gui/                  # GUI приложение
│   ├── __init__.py
│   └── main.py          # PyQt6 интерфейс
├── cli/                  # CLI интерфейс
│   ├── __init__.py
│   └── main.py          # Click интерфейс
├── web/                  # WEB приложение
│   ├── __init__.py
│   ├── app.py           # Flask приложение
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
- `get_temperature(interface)`: Получение температуры
- `get_statistics(interface)`: Получение статистики

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
- `temperature`: Температура

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

### v1.0.0
- Первоначальный релиз
- Поддержка GUI, CLI и WEB интерфейсов
- Поддержка PPS и TCXO
- Мониторинг в реальном времени
- Поддержка драйверов IGB, I40E, IXGBE