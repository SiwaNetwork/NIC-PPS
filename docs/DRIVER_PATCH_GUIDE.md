# Руководство по применению патча драйвера igc для решения проблемы с фронтами PPS

## 🎯 Цель патча

Этот патч решает проблему привязки заднего фронта PPS NIC карты к переднему фронту основных часов, которая возникает из-за того, что драйвер igc по умолчанию может детектировать оба фронта PPS сигнала.

## 📋 Что делает патч

1. **Принудительное использование только восходящего фронта** - все PPS события принудительно настраиваются на восходящий фронт
2. **Фильтрация событий на уровне драйвера** - проверка уровня пина после прерывания для исключения ложных событий
3. **Отслеживание конфигурации** - сохранение настроек пинов и флагов для корректной обработки

## 🔧 Применение патча

### Шаг 1: Подготовка исходного кода ядра

```bash
# Установка необходимых пакетов
sudo apt update
sudo apt install linux-headers-$(uname -r) linux-source-$(uname -r) build-essential

# Распаковка исходного кода
cd /usr/src
sudo tar -xf linux-source-$(uname -r).tar.bz2
cd linux-source-$(uname -r)
```

### Шаг 2: Применение патча

Создайте файл с патчем:

```bash
sudo nano /usr/src/linux-source-$(uname -r)/igc_pps_fix.patch
```

Вставьте содержимое патча (предоставленного пользователем).

Примените патч:

```bash
cd /usr/src/linux-source-$(uname -r)
sudo patch -p1 < igc_pps_fix.patch
```

### Шаг 3: Сборка драйвера

```bash
# Настройка конфигурации ядра
sudo make oldconfig

# Сборка только модуля igc
sudo make modules_prepare
sudo make M=drivers/net/ethernet/intel/igc
```

### Шаг 4: Установка нового драйвера

```bash
# Создание резервной копии старого драйвера
sudo cp /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/igc.ko \
        /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/igc.ko.backup

# Установка нового драйвера
sudo cp drivers/net/ethernet/intel/igc/igc.ko \
        /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/

# Обновление модулей
sudo depmod -a
```

### Шаг 5: Перезагрузка драйвера

```bash
# Отключение интерфейса
sudo ip link set enp3s0 down

# Выгрузка старого драйвера
sudo modprobe -r igc

# Загрузка нового драйвера
sudo modprobe igc

# Включение интерфейса
sudo ip link set enp3s0 up
```

## 🧪 Тестирование патча

### Проверка работы PPS

```bash
# Включение PPS входа
sudo testptp -d /dev/ptp0 -L1,1

# Чтение PPS событий (должно быть только одно событие на импульс)
sudo testptp -d /dev/ptp0 -e 10
```

### Ожидаемые результаты

- **До патча**: Два события на один PPS импульс (восходящий и нисходящий фронты)
- **После патча**: Одно событие на один PPS импульс (только восходящий фронт)

### Диагностика с помощью нашего скрипта

```bash
cd /home/shiwa-time/NIC-PPS
source venv/bin/activate
python scripts/diagnose_pps_edges.py
```

## 🔄 Откат изменений

Если патч вызывает проблемы:

```bash
# Восстановление оригинального драйвера
sudo cp /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/igc.ko.backup \
        /lib/modules/$(uname -r)/kernel/drivers/net/ethernet/intel/igc/igc.ko

# Перезагрузка драйвера
sudo modprobe -r igc
sudo modprobe igc
```

## ⚠️ Важные замечания

1. **Резервное копирование**: Всегда создавайте резервные копии оригинальных файлов
2. **Тестирование**: Тщательно тестируйте патч перед использованием в продакшене
3. **Совместимость**: Патч может потребовать адаптации для других версий ядра
4. **Права доступа**: Некоторые операции требуют прав root

## 🐛 Устранение неполадок

### Проблема: Драйвер не загружается
```bash
# Проверка логов
dmesg | grep igc

# Проверка зависимостей
modinfo igc
```

### Проблема: PPS события не работают
```bash
# Проверка PTP устройств
ls -la /dev/ptp*

# Проверка конфигурации
sudo testptp -d /dev/ptp0 -l
```

### Проблема: Интерфейс не поднимается
```bash
# Проверка статуса интерфейса
ip link show enp3s0

# Перезапуск сетевого сервиса
sudo systemctl restart networking
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи ядра: `dmesg | tail -50`
2. Используйте диагностический скрипт
3. Обратитесь к документации linuxptp
4. Проверьте совместимость версий ядра

## 🔗 Связанные файлы

- `scripts/diagnose_pps_edges.py` - Диагностика проблем с фронтами PPS
- `core/timenic_manager.py` - Менеджер TimeNIC с улучшенной настройкой фронтов
- `core/nic_manager.py` - Менеджер NIC с поддержкой ts2phc rising edge
