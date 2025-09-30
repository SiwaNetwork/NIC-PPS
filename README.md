# 🚀 SHIWA NIC-PPS Configuration and Monitoring Tool

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](https://github.com/shiwa-time/NIC-PPS)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

Инструмент для настройки и мониторинга Intel NIC с поддержкой PPS (Pulse Per Second), PHC (PTP Hardware Clock) синхронизации и TimeNIC карт.

## ✨ Основные возможности

### 🎯 Поддерживаемые функции:

- **PPS конфигурация** - настройка Pulse Per Second сигналов
- **PHC синхронизация** - синхронизация PTP Hardware Clock между устройствами
- **TimeNIC поддержка** - работа с Intel I226 картами (SMA, TCXO, PTM)
- **Автоматический watchdog** - мониторинг и перезапуск phc2sys при сбоях
- **Диагностика PPS** - проверка привязки к переднему фронту и стабильности
- **Три интерфейса** - GUI, CLI и WEB для управления системой

### 🔧 Поддерживаемое оборудование:

- Intel I210 / I211 (базовая поддержка PPS)
- Intel I226 / TimeNIC (расширенная поддержка: SMA, TCXO, PTM)
- Другие Intel NIC с поддержкой PTP

## 📦 Установка

### Требования:

```bash
# Системные пакеты
sudo apt-get install -y \
    python3-venv \
    python3-pip \
    linuxptp \
    ethtool \
    build-essential

# Опционально для TimeNIC
sudo apt-get install -y libgpiod-dev
```

### Установка проекта:

```bash
# Клонируем репозиторий
git clone https://github.com/shiwa-time/NIC-PPS.git
cd NIC-PPS

# Создаем виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Настраиваем sudo права (один раз)
bash scripts/setup_sudo_permissions.sh
```

## 🚀 Быстрый старт

### 1. GUI интерфейс:

```bash
python run.py --gui
```

**Возможности GUI:**
- ✅ Визуальная настройка PPS режимов
- ✅ Управление PHC синхронизацией
- ✅ Кнопка "🔍 Диагностика PPS" для проверки системы
- ✅ Мониторинг в реальном времени
- ✅ Настройка TimeNIC параметров

### 2. WEB интерфейс:

```bash
python run.py --web
# Откройте http://localhost:5000 в браузере
```

**Преимущества WEB:**
- ✅ Удаленный доступ через браузер
- ✅ Адаптивный дизайн
- ✅ Real-time обновления через WebSocket
- ✅ Графики и метрики
- ✅ Не требует X11

### 3. CLI интерфейс:

```bash
# Диагностика PPS
python run.py --cli timenic check-pps

# Список карт
python run.py --cli timenic list-timenics

# Установка PPS режима
python run.py --cli timenic set-pps enp3s0 --mode output

# Синхронизация PHC
python run.py --cli timenic start-phc-sync enp3s0

# Статус системы
python run.py --cli timenic status
```

## 📊 Основные команды

### TimeNIC команды:

```bash
# Полная диагностика PPS и phc2sys
python run.py --cli timenic check-pps

# Список всех TimeNIC карт
python run.py --cli timenic list-timenics

# Информация о конкретной карте
python run.py --cli timenic info enp3s0

# Установка PPS режима (disabled, input, output, both)
python run.py --cli timenic set-pps enp3s0 --mode output

# Список PTP устройств
python run.py --cli timenic list-ptp

# Чтение PPS событий
python run.py --cli timenic read-pps /dev/ptp0 --count 5

# Установка периода PPS (в наносекундах)
python run.py --cli timenic set-period /dev/ptp0 --period 1000000000

# Синхронизация PHC с системным временем
python run.py --cli timenic sync-phc enp3s0

# Запуск синхронизации PHC по внешнему PPS
python run.py --cli timenic start-phc-sync enp3s0

# Включение PTM
python run.py --cli timenic enable-ptm enp3s0

# Мониторинг карты
python run.py --cli timenic monitor enp3s0 --interval 1

# Создание systemd сервиса
sudo python run.py --cli timenic create-service

# Общий статус системы
python run.py --cli timenic status
```

### Обычные NIC команды:

```bash
# Диагностика
python run.py --cli check-pps

# Список всех карт
python run.py --cli list-nics

# Информация о карте
python run.py --cli info enp3s0

# Статус синхронизации
python run.py --cli sync-status
```

## 🔧 Прямые скрипты

### 1. Диагностика PPS:

```bash
python scripts/check_pps_edge.py
```

Проверяет:
- ✅ Запущен ли phc2sys
- ✅ Привязка к переднему фронту (восходящий edge)
- ✅ Стабильность phc2sys (0 падений)

### 2. Watchdog мониторинг:

```bash
# Запускается автоматически через GUI/WEB
# Или вручную:
bash scripts/phc_watchdog.sh /dev/ptp2 /dev/ptp0 0 16
```

Параметры:
- `source_ptp` - источник времени (например, /dev/ptp2)
- `target_ptp` - целевое устройство (например, /dev/ptp0)
- `offset_ns` - смещение в наносекундах (0 для без смещения)
- `rate` - частота обновления в Гц (16 рекомендуется)

### 3. Исправление PPS края:

```bash
bash scripts/fix_pps_edge.sh /dev/ptp0 1
```

Настраивает пин только на восходящий фронт.

## 🏗️ Архитектура проекта

```
NIC-PPS/
├── core/                       # Основная логика
│   ├── nic_manager.py         # Менеджер Intel NIC
│   ├── timenic_manager.py     # Менеджер TimeNIC
│   └── pps_edge_filter.py     # Фильтрация PPS событий
├── gui/                        # GUI интерфейс (PyQt6)
│   └── main.py                # Главное окно
├── web/                        # WEB интерфейс (Flask)
│   ├── app.py                 # Flask приложение
│   ├── templates/             # HTML шаблоны
│   └── static/                # CSS, JS, изображения
├── cli/                        # CLI интерфейс (Click)
│   ├── main.py                # CLI для обычных NIC
│   └── timenic_cli.py         # CLI для TimeNIC
├── scripts/                    # Утилиты и скрипты
│   ├── check_pps_edge.py      # Диагностика PPS
│   ├── phc_watchdog.sh        # Watchdog для phc2sys
│   ├── fix_pps_edge.sh        # Исправление PPS края
│   ├── setup_sudo_permissions.sh  # Настройка sudo
│   └── deprecated/            # Устаревшие скрипты
├── docs/                       # Документация
├── tests/                      # Тесты
├── run.py                      # Главный запускатель
├── requirements.txt            # Python зависимости
├── SETUP_GUIDE.md             # Подробное руководство
└── README.md                   # Этот файл
```

## 🐛 Устранение неполадок

### Проблема: phc2sys не запускается

**Решение:**
```bash
# 1. Проверьте sudo права
sudo -n phc2sys --help

# 2. Если требует пароль:
bash scripts/setup_sudo_permissions.sh

# 3. Проверьте устройства
ls -la /dev/ptp*

# 4. Проверьте драйверы
lsmod | grep -E "ptp|igc|i210"
```

### Проблема: PPS привязывается к заднему фронту

**Решение:**
```bash
# Используйте скрипт исправления
bash scripts/fix_pps_edge.sh /dev/ptp0 1

# Проверьте результат
python scripts/check_pps_edge.py
```

### Проблема: rate=0.0 ошибка

**Исправлено в версии 1.2.0!**
- Теперь rate по умолчанию 16 Гц
- Диапазон: 1.0 - 1000.0 Гц
- Валидация в watchdog скрипте

### Проблема: GUI крашится

**Решение:**
```bash
# Используйте WEB интерфейс как альтернативу
python run.py --web

# Или запустите GUI с отладкой
python run.py --gui 2>&1 | tee gui_debug.log
```

## 📈 История изменений

### Версия 1.2.0 (30.09.2025)

**🔧 Исправления:**
- ✅ Исправлен `rate=0.0` bug - теперь по умолчанию 16 Гц
- ✅ Исправлен watchdog - правильная проверка процессов
- ✅ Добавлена валидация rate в phc_watchdog.sh
- ✅ Настройка sudo прав через скрипт

**✨ Новые возможности:**
- ✅ Кнопка "🔍 Диагностика PPS" в GUI
- ✅ Команда `check-pps` в CLI
- ✅ Скрипт `setup_sudo_permissions.sh`
- ✅ Tooltip для поля rate в GUI

**🧹 Очистка кода:**
- ✅ Удалено 168 строк мертвого кода (-9.7%)
- ✅ Удалены устаревшие методы агрессивного мониторинга
- ✅ Перемещены устаревшие скрипты в `scripts/deprecated/`

### Версия 1.1.0

- ✅ Добавлена поддержка TimeNIC
- ✅ Watchdog мониторинг для phc2sys
- ✅ WEB интерфейс

### Версия 1.0.0

- ✅ Базовая поддержка Intel NIC
- ✅ GUI и CLI интерфейсы
- ✅ PPS конфигурация

## 📚 Дополнительная документация

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Подробное руководство по настройке
- [docs/DRIVER_PATCH_GUIDE.md](docs/DRIVER_PATCH_GUIDE.md) - Патчинг драйвера igc
- [docs/timenic_pps_commands.md](docs/timenic_pps_commands.md) - Команды для TimeNIC
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Устранение неполадок
- [scripts/deprecated/README.md](scripts/deprecated/README.md) - Устаревшие скрипты

## 🤝 Вклад в проект

Приветствуются pull requests! Для больших изменений сначала откройте issue для обсуждения.

## 📝 Лицензия

[MIT](LICENSE)

## 👥 Авторы

- **SHIWA Team** - [GitHub](https://github.com/shiwa-time)

## 🙏 Благодарности

- Linux PTP проект за `linuxptp` утилиты
- Intel за документацию по PTP Hardware Clock
- Сообщество open source за поддержку

## 📧 Контакты

Если у вас есть вопросы или предложения, создайте issue на GitHub.

---

**Made with ❤️ by SHIWA Team**