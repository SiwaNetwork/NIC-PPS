# 🧾 Изменения для поддержки TimeNIC

## Обзор изменений

Программа была переделана для поддержки **TimeNIC карт (Intel I226 NIC, SMA, TCXO)** согласно инструкции. Добавлена полная поддержка PPS, PTP, SMA разъемов и TCXO.

## 📁 Новые файлы

### Core модули
- `core/timenic_manager.py` - Менеджер для работы с TimeNIC картами
- `cli/timenic_cli.py` - CLI интерфейс для TimeNIC команд
- `docs/TIMENIC_SETUP.md` - Подробная документация по настройке TimeNIC
- `scripts/setup_timenic.sh` - Автоматический скрипт настройки TimeNIC
- `examples/timenic_config.json` - Пример конфигурации TimeNIC

## 🔧 Измененные файлы

### requirements.txt
- Добавлены зависимости для TimeNIC: `linuxptp`, `ptp-tools`, `gpiod`
- Добавлены системные зависимости: `chrony`, `ntp`, `systemd-python`, `dbus-python`

### run.py
- Обновлена проверка зависимостей для TimeNIC модулей
- Добавлена поддержка команды `timenic` в CLI
- Обновлена проверка системы для TimeNIC карт и PTP устройств
- Обновлена справка с командами TimeNIC

### core/__init__.py
- Добавлены импорты для TimeNIC менеджера
- Добавлены новые классы: `TimeNICManager`, `TimeNICInfo`, `PTPInfo`, `PTMStatus`

### README.md
- Добавлена информация о поддержке TimeNIC
- Обновлены CLI команды с разделением на обычные NIC и TimeNIC
- Добавлены специфичные возможности TimeNIC
- Обновлена документация

### INSTALL.md
- Добавлены требования для TimeNIC
- Обновлены udev правила для драйвера igc
- Добавлен раздел установки TimeNIC
- Добавлена поддержка TimeNIC

## 🚀 Новые возможности

### TimeNIC Manager (core/timenic_manager.py)
- **Обнаружение TimeNIC карт** с драйвером igc
- **PTP устройств** в системе
- **Управление PPS режимами**: disabled, input, output, both
- **SMA разъемы**: SMA1 (SDP0) - выход PPS, SMA2 (SDP1) - вход PPS
- **TCXO управление**: Температурно-компенсированный кварцевый генератор
- **PHC синхронизация**: Коррекция времени по внешнему PPS
- **PTM поддержка**: PCIe Time Management
- **Установка драйвера**: Автоматическая установка патченного драйвера
- **Systemd сервис**: Создание автозапуска

### TimeNIC CLI (cli/timenic_cli.py)
- `list-timenics` - Список всех TimeNIC карт
- `info <interface>` - Подробная информация о TimeNIC карте
- `set-pps <interface> --mode <mode>` - Настройка PPS режима
- `set-tcxo <interface> --enable/--disable` - Управление TCXO
- `start-phc-sync <interface>` - Запуск синхронизации PHC
- `enable-ptm <interface>` - Включение PTM
- `list-ptp` - Список PTP устройств
- `monitor <interface> --interval <sec>` - Мониторинг в реальном времени
- `install-driver` - Установка драйвера TimeNIC
- `create-service` - Создание systemd сервиса
- `read-pps <ptp_device> --count <count>` - Чтение PPS событий
- `set-period <ptp_device> --period <ns>` - Установка периода
- `status` - Общий статус TimeNIC системы
- `config --output <file>` - Сохранение конфигурации

## 📋 Поддерживаемые функции согласно инструкции

### ✅ Генерация 1 Гц (PPS) через SDP0 → SMA1
```bash
python run.py --cli timenic set-pps eth0 --mode output
```

### ✅ Приём внешнего PPS через SDP1 → SMA2
```bash
python run.py --cli timenic set-pps eth0 --mode input
```

### ✅ Синхронизация PHC по внешнему сигналу
```bash
python run.py --cli timenic start-phc-sync eth0
```

### ✅ Использование PTM (PCIe Time Management)
```bash
python run.py --cli timenic enable-ptm eth0
```

### ✅ Работа с linuxptp, testptp, ts2phc
- Автоматическая установка и настройка утилит
- Интеграция в CLI команды
- Мониторинг и диагностика

## 🔧 Технические детали

### Обнаружение TimeNIC карт
- Проверка драйвера `igc` (Intel I226)
- Поиск PTP устройств в `/dev/ptp*`
- Получение информации через `ethtool -T`

### Управление PPS
- Использование `testptp` для настройки SDP пинов
- SDP0 (SMA1) - периодический выход
- SDP1 (SMA2) - внешние временные метки
- Период 1 Гц = 1000000000 наносекунд

### PHC синхронизация
- Использование `ts2phc` для коррекции времени
- Мониторинг offset и frequency
- Интеграция с внешними PPS источниками

### Systemd интеграция
- Автоматическое создание сервиса `ptp-nic-setup`
- Настройка автозапуска при загрузке
- Мониторинг статуса сервиса

## 📖 Документация

### Основная документация
- `docs/TIMENIC_SETUP.md` - Подробная инструкция по настройке
- `README.md` - Обновленная документация с TimeNIC командами
- `INSTALL.md` - Инструкции по установке с TimeNIC

### Примеры
- `examples/timenic_config.json` - Пример конфигурации
- `scripts/setup_timenic.sh` - Автоматический скрипт настройки

## 🧪 Тестирование

### Проверка установки
```bash
# Проверка системы
python run.py --check

# Список TimeNIC карт
python run.py --cli timenic list-timenics

# Статус системы
python run.py --cli timenic status
```

### Тестирование PPS
```bash
# Настройка PPS
python run.py --cli timenic set-pps eth0 --mode both

# Чтение PPS событий
python run.py --cli timenic read-pps /dev/ptp0 --count 5

# Мониторинг
python run.py --cli timenic monitor eth0 --interval 1
```

## 🔗 Ссылки

- [TimeNIC GitHub](https://github.com/Time-Appliances-Project/Products/tree/main/TimeNIC)
- [PTM Readiness List](https://www.opencompute.org/wiki/PTM_Readiness)
- [OCP TAP Wiki](https://www.opencompute.org/wiki/Time_Appliances_Project)

## 📌 Заключение

Программа успешно переделана для поддержки TimeNIC карт с полной реализацией всех функций из инструкции:

- ✅ Генерация 1 Гц через SMA1
- ✅ Приём внешнего PPS через SMA2
- ✅ Синхронизация PHC по внешнему PPS
- ✅ Поддержка PTM (при наличии аппаратной поддержки)
- ✅ Интеграция с linuxptp, testptp, ts2phc
- ✅ Автоматическая установка и настройка
- ✅ Мониторинг и диагностика
- ✅ Systemd интеграция

Все изменения обратно совместимы с существующими обычными NIC картами.