# SHIWA NIC-PPS Configuration and Monitoring Tool

**Версия:** 1.2.0  
**Дата сборки:** 2025-09-10

Комплексное решение для конфигурации и мониторинга сетевых карт Intel с поддержкой PPS (Pulse Per Second), TimeNIC, TCXO и PHC синхронизации.

## 🎯 Что нового в v1.2.0

- ✨ **Современный веб-интерфейс** - обновленный дизайн с градиентами, анимациями и улучшенной навигацией
- 📊 **Система мониторинга и метрик** - Prometheus метрики, health checks, мониторинг в реальном времени
- 🧪 **Тестирование** - полное покрытие тестами с pytest и coverage
- 🔧 **Исправлен мониторинг трафика** - поддержка любых активных интерфейсов (включая WiFi)
- 🎨 **Улучшенный UX** - быстрые действия, горячие клавиши, адаптивный дизайн

## Возможности

- **PPS поддержка**: Настройка и мониторинг PPS сигналов (входной, выходной, оба режима)
- **TCXO поддержка**: Управление температурно-компенсированными кварцевыми генераторами
- **PHC синхронизация**: Взаимная синхронизация между PHC часами (`phc2sys`) и синхронизация по внешнему PPS (`ts2phc`)
- **PTP мониторинг**: Мониторинг PTP трафика и статистики
- **Многоплатформенность**: GUI, CLI и WEB интерфейсы
- **Автоматическое обнаружение**: Intel NIC карт и PTP устройств
- **Современный веб-интерфейс**: Адаптивный дизайн, анимации, быстрые действия
- **Система метрик**: Prometheus метрики, health checks, мониторинг системы
- **Универсальный мониторинг**: Поддержка любых сетевых интерфейсов (Ethernet, WiFi)
- **Тестирование**: Полное покрытие тестами с автоматической проверкой

## Быстрый старт

### Установка зависимостей

```bash
# Системные пакеты
sudo apt update
sudo apt install -y linuxptp gcc build-essential ethtool

# Python зависимости
pip install -r requirements.txt
```

### Настройка sudo прав

```bash
# Создание файла sudoers для PPS команд
echo 'shiwa-time ALL=(ALL) NOPASSWD: /usr/bin/testptp, /usr/bin/phc_ctl, /usr/bin/ts2phc, /usr/bin/phc2sys' | sudo tee /etc/sudoers.d/nic-pps

# Проверка прав
sudo -n testptp -d /dev/ptp0 -l
```

### Запуск приложения

```bash
# GUI интерфейс
python run.py --gui

# CLI интерфейс
python run.py --cli

# WEB интерфейс
python run.py --web
# Откройте браузер: http://localhost:5000
```

## Использование

### CLI команды

```bash
# Список всех NIC карт
python run.py --cli list-nics

# Настройка PPS режима
python run.py --cli set-pps enp3s0 --mode output

# PHC синхронизация
python run.py --cli start-phc-sync /dev/ptp0 /dev/ptp1
python run.py --cli start-ts2phc-sync enp3s0 /dev/ptp0

# Мониторинг
python run.py --cli monitor enp3s0 --interval 1

# Статус
python run.py --cli status
```

### TimeNIC команды

```bash
# TimeNIC PPS настройка
python run.py --cli timenic set-pps enp3s0 --mode both

# TimeNIC PHC синхронизация
python run.py --cli timenic start-phc-sync /dev/ptp0 /dev/ptp1
python run.py --cli timenic start-ts2phc-sync enp3s0 /dev/ptp0
```

### Веб-интерфейс

Современный веб-интерфейс с множеством возможностей:

#### 🎨 **Современный дизайн**
- Градиентные фоны и стеклянные эффекты
- Плавные анимации и переходы
- Адаптивный дизайн для всех устройств
- Темная тема с автоматическим переключением

#### 🚀 **Быстрые действия**
- **Обновить все** - обновление всех данных
- **Запустить мониторинг** - переход к мониторингу
- **Проверить систему** - переход к метрикам
- **Экспорт логов** - экспорт системных логов

#### ⌨️ **Горячие клавиши**
- `Alt + 1` - Обзор
- `Alt + 2` - TimeNIC  
- `Alt + 3` - Настройки
- `Alt + 4` - Метрики
- `Alt + 5` - Мониторинг

#### 📊 **Мониторинг и метрики**
- **Prometheus метрики** - `/metrics` endpoint
- **Health checks** - `/api/health` endpoint
- **Мониторинг трафика** - поддержка любых интерфейсов
- **Реальное время** - обновление каждые 2 секунды

#### 🔧 **Универсальный мониторинг**
- Автоматическое определение активных интерфейсов
- Поддержка Ethernet и WiFi интерфейсов
- Графики трафика в реальном времени
- Статистика PTP и сетевого трафика

## Установка драйвера Intel IGC

### Шаг 1: Установка драйвера

```bash
chmod +x install_igc_pps.sh
sudo ./install_igc_pps.sh
```

### Шаг 2: Перезагрузка

```bash
sudo reboot
```

### Шаг 3: Настройка PPS

```bash
# Интерактивная настройка
sudo ./configure_pps.sh

# Или быстрая настройка
sudo ./quick_pps_setup.sh
```

## Описание PPS

### Для Intel I210 (основная сетевая карта):
- **SDP0** - PPS выход на разъем INTEL I210, генерирует сигнал 1PPS (1 импульс в секунду)
- **SDP1** - PPS вход, принимает внешний PPS сигнал

### Для TimeNIC (SMA разъемы):
- **SMA1** - PPS выход, генерирует сигнал 1PPS
- **SMA2** - PPS вход, принимает внешний PPS сигнал

## PHC синхронизация

### Mutual PHC Synchronization (phc2sys)

Синхронизация между двумя PTP Hardware Clocks:

```bash
# Запуск взаимной синхронизации
python run.py --cli start-phc-sync /dev/ptp0 /dev/ptp1

# Проверка статуса
python run.py --cli sync-status

# Остановка
python run.py --cli stop-phc-sync
```

### External PPS Synchronization (ts2phc)

Синхронизация PHC по внешнему PPS сигналу:

```bash
# Запуск синхронизации по внешнему PPS
python run.py --cli start-ts2phc-sync enp3s0 /dev/ptp0

# Остановка
python run.py --cli stop-ts2phc-sync
```

## Тестирование

```bash
# Запуск всех тестов
python run_tests.py

# Запуск с покрытием
python run_tests.py --coverage

# Запуск конкретных тестов
pytest tests/test_nic_manager.py
pytest tests/test_web_app.py
pytest tests/test_metrics.py
```

## Проверка установки

```bash
# Проверка драйвера
modinfo igc | grep filename
ethtool -i enp3s0

# Проверка PPS
sudo testptp -d /dev/ptp0 -l

# Проверка PTP устройств
ls /dev/ptp*

# Проверка веб-интерфейса
curl http://localhost:5000/api/health
curl http://localhost:5000/api/interfaces/active
```

## Дополнительные команды

### Чтение PPS событий

```bash
sudo testptp -d /dev/ptp0 -e 10  # читает 10 событий
```

### Изменение частоты PPS выхода

```bash
# 10 Гц (100ms период)
sudo testptp -d /dev/ptp0 -p 100000000

# 0.5 Гц (2 секунды период)  
sudo testptp -d /dev/ptp0 -p 2000000000
```

### Ручное управление PPS

```bash
# Включение выходного PPS
sudo testptp -d /dev/ptp0 -L0,2
sudo testptp -d /dev/ptp0 -p 1000000000

# Включение входного PPS
sudo testptp -d /dev/ptp0 -L1,1

# Отключение PPS
sudo testptp -d /dev/ptp0 -p 0
sudo testptp -d /dev/ptp0 -L0,0
sudo testptp -d /dev/ptp0 -L1,0
```

## Требования

- Ubuntu/Debian Linux
- Сетевая карта Intel с чипом IGC (i225/i226)
- Python 3.8+
- Права root для установки
- DKMS для сборки драйвера
- Установленные утилиты: `ethtool`, `testptp`, `phc_ctl`, `ts2phc`, `phc2sys`

## Устранение проблем

### Драйвер не загрузился

```bash
# Проверка загруженного модуля
lsmod | grep igc

# Ручная загрузка
sudo modprobe igc

# Проверка логов
dmesg | grep igc
```

### PPS не работает

```bash
# Проверка текущего состояния PPS
sudo testptp -d /dev/ptp0 -l

# Проверка sudo прав
sudo -n testptp -d /dev/ptp0 -l

# Проверка PTP устройства
ethtool -T enp3s0
```

### PHC синхронизация не работает

```bash
# Проверка процессов синхронизации
ps aux | grep -E "(phc2sys|ts2phc)"

# Проверка PTP устройств
ls /dev/ptp*

# Проверка статуса синхронизации
python run.py --cli sync-status
```

## Документация

Подробная документация находится в папке `docs/`:

- [Основная документация](docs/README.md)
- [TimeNIC команды](docs/timenic_pps_commands.md)
- [Настройка TimeNIC](docs/TIMENIC_SETUP.md)
- [Устранение неполадок](TROUBLESHOOTING.md)
- [История изменений](CHANGELOG.md)

## История версий

### v1.2.0 (2025-09-10)
- ✨ **Современный веб-интерфейс**: Обновленный дизайн с градиентами, анимациями и улучшенной навигацией
- 📊 **Система мониторинга и метрик**: Prometheus метрики, health checks, мониторинг в реальном времени
- 🧪 **Тестирование**: Полное покрытие тестами с pytest и coverage
- 🔧 **Исправлен мониторинг трафика**: Поддержка любых активных интерфейсов (включая WiFi)
- 🎨 **Улучшенный UX**: Быстрые действия, горячие клавиши, адаптивный дизайн
- 🚀 **Новые возможности**: Универсальный мониторинг, автоматическое определение интерфейсов

### v1.1.0 (2025-09-09)
- 🐛 **Критическое исправление**: Исправлено определение PTP устройства для Intel I210
- ✨ **Система версионирования**: Добавлено отображение версии в GUI, веб-интерфейсе и API
- 🔧 **Улучшения**: Исправлены проблемы с кнопками включения/выключения PPS в GUI
- 📚 **Документация**: Обновлена документация с актуальной информацией

### v1.0.0 (2025-09-09)
- 🎉 **Первоначальный релиз**
- 🖥️ **Интерфейсы**: GUI (PyQt6), CLI, WEB (Flask)
- ⚡ **PPS поддержка**: Настройка и мониторинг PPS сигналов
- 🔄 **PHC синхронизация**: phc2sys и ts2phc
- 📊 **Мониторинг**: PTP трафик, статистика, реальное время
- 🔧 **Поддержка**: Intel NIC карты, TimeNIC, TCXO