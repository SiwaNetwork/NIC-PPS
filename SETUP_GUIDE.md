# 🚀 Руководство по настройке NIC-PPS

## ✅ Быстрый старт

### 1. Настройка sudo прав (один раз)

Для работы PTP утилит без постоянного ввода пароля выполните:

```bash
cd /home/shiwa-time/NIC-PPS
bash scripts/setup_sudo_permissions.sh
```

После этого введите пароль один раз. Больше пароль не понадобится.

### 2. Проверка настроек

```bash
# Проверяем что утилиты работают без пароля
sudo -n phc2sys --help 2>&1 | head -2
sudo -n testptp -d /dev/ptp0 -g 2>&1 | head -2
sudo -n phc_ctl /dev/ptp0 get 2>&1 | head -2
```

Если вы видите результаты без запроса пароля - всё настроено правильно!

### 3. Запуск GUI

```bash
cd /home/shiwa-time/NIC-PPS
source venv/bin/activate
python run.py --gui
```

## 📊 Доступные команды

### CLI команды

#### TimeNIC команды:

```bash
# Полная диагностика PPS
python run.py --cli timenic check-pps

# Список TimeNIC карт
python run.py --cli timenic list-timenics

# Информация о карте
python run.py --cli timenic info enp3s0

# Установка PPS режима
python run.py --cli timenic set-pps enp3s0 --mode output

# Чтение PPS событий
python run.py --cli timenic read-pps /dev/ptp0 --count 5

# Синхронизация PHC
python run.py --cli timenic start-phc-sync enp3s0

# Общий статус системы
python run.py --cli timenic status
```

#### Обычные NIC команды:

```bash
# Диагностика PPS
python run.py --cli check-pps

# Список всех карт
python run.py --cli list-nics

# Информация о карте
python run.py --cli info enp3s0

# Статус синхронизации
python run.py --cli sync-status
```

### Прямые скрипты

#### 1. Диагностика PPS:
```bash
python scripts/check_pps_edge.py
```

Проверяет:
- ✅ Запущен ли phc2sys
- ✅ Привязка к переднему фронту
- ✅ Стабильность phc2sys

#### 2. Исправление PPS края:
```bash
bash scripts/fix_pps_edge.sh /dev/ptp0 1
```

Настраивает пин только на восходящий фронт.

#### 3. Мониторинг phc2sys:
```bash
# Запускается автоматически через GUI
# Или вручную:
bash scripts/phc_watchdog.sh /dev/ptp2 /dev/ptp0 0 16
```

Параметры:
- `source_ptp` - источник времени (например, /dev/ptp2)
- `target_ptp` - целевое устройство (например, /dev/ptp0)
- `offset_ns` - смещение в наносекундах
- `rate` - частота обновления

## 🔧 Устранение неполадок

### Проблема: phc2sys не запускается

**Решение:**
```bash
# 1. Проверьте sudo права
sudo -n phc2sys --help

# 2. Если требует пароль, выполните:
bash scripts/setup_sudo_permissions.sh

# 3. Перезапустите GUI
pkill -9 -f "python run.py"
python run.py --gui
```

### Проблема: PPS привязывается к заднему фронту

**Решение:**
```bash
# Используйте скрипт исправления
bash scripts/fix_pps_edge.sh /dev/ptp0 1

# Проверьте результат
python scripts/check_pps_edge.py
```

### Проблема: GUI не показывает устройства

**Решение:**
```bash
# 1. Проверьте наличие PTP устройств
ls -la /dev/ptp*

# 2. Проверьте драйверы
lsmod | grep -E "ptp|igc|i210"

# 3. Проверьте права доступа
ls -la /dev/ptp*

# 4. Перезапустите GUI с отладкой
python run.py --gui 2>&1 | tee gui_debug.log
```

## 📁 Структура проекта

```
NIC-PPS/
├── core/                    # Основные модули
│   ├── nic_manager.py      # Менеджер Intel NIC
│   └── timenic_manager.py  # Менеджер TimeNIC
├── gui/                     # GUI интерфейс
│   └── main.py             # Главное окно
├── cli/                     # CLI интерфейс
│   ├── main.py             # CLI для обычных NIC
│   └── timenic_cli.py      # CLI для TimeNIC
├── scripts/                 # Утилиты
│   ├── check_pps_edge.py   # Диагностика PPS
│   ├── phc_watchdog.sh     # Мониторинг phc2sys
│   ├── fix_pps_edge.sh     # Исправление PPS края
│   └── deprecated/         # Устаревшие скрипты
└── run.py                   # Главный запускатель

```

## 🎯 Рекомендуемый рабочий процесс

### Первый запуск:

1. **Настройте sudo права:**
   ```bash
   bash scripts/setup_sudo_permissions.sh
   ```

2. **Запустите GUI:**
   ```bash
   python run.py --gui
   ```

3. **В GUI:**
   - Выберите TimeNIC карту (enp3s0)
   - Установите PPS режим: **output**
   - Нажмите "🔍 Диагностика PPS"
   - Проверьте что всё работает ✅

### Для синхронизации:

1. **В GUI:**
   - Выберите источник (например, /dev/ptp2)
   - Выберите цель (например, /dev/ptp0)
   - Установите offset если нужен
   - Нажмите "Запустить синхронизацию"

2. **Watchdog автоматически:**
   - Запустит phc2sys
   - Будет мониторить процесс
   - Перезапустит при падении

3. **Проверка стабильности:**
   - Нажмите "🔍 Диагностика PPS"
   - Проверьте логи: `tail -f /tmp/phc_watchdog.log`

## 🆘 Получение помощи

Если у вас возникли проблемы:

1. Проверьте логи:
   ```bash
   # Лог watchdog
   tail -f /tmp/phc_watchdog.log
   
   # Лог phc2sys
   tail -f /tmp/phc2sys.log
   
   # Лог диагностики
   python scripts/check_pps_edge.py
   ```

2. Запустите полную диагностику:
   ```bash
   python run.py --cli timenic check-pps
   ```

3. Проверьте систему:
   ```bash
   python run.py --check
   ```

## ✨ Новые возможности

После очистки кода (30.09.2025):

- ✅ Удалено 168 строк мертвого кода (-9.7%)
- ✅ Добавлена кнопка диагностики PPS в GUI
- ✅ Улучшен watchdog мониторинг
- ✅ Добавлена настройка sudo прав
- ✅ Оптимизирована структура проекта

Проект готов к работе! 🎉
