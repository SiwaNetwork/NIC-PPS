# Решение проблемы установки драйвера TimeNIC

## Проблема
При запуске скрипта установки TimeNIC возникала ошибка:
```
Error! DKMS tree already contains: igc-5.4.0-7642.46
You cannot add the same module/version combo more than once.
```

## Причина
Модуль igc уже был частично добавлен в DKMS, но не был полностью установлен из-за несоответствия версий ядра.

## Решение

### 1. Установка DKMS (если не установлен)
```bash
sudo apt-get update
sudo apt-get install -y dkms
```

### 2. Загрузка и распаковка драйвера TimeNIC
```bash
cd /tmp
wget -q https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip
unzip -q intel-igc-ppsfix_ubuntu.zip
cd intel-igc-ppsfix
```

### 3. Удаление старого модуля (если существует)
```bash
sudo dkms remove igc/5.4.0-7642.46 --all 2>/dev/null || true
```

### 4. Добавление модуля в DKMS
```bash
sudo dkms add .
```

### 5. Сборка модуля для доступной версии ядра
```bash
# Для ядра с установленными заголовками (в данном случае 6.14.0-24-generic)
sudo dkms build igc/5.4.0-7642.46 -k 6.14.0-24-generic
```

### 6. Установка модуля
```bash
sudo dkms install igc/5.4.0-7642.46 -k 6.14.0-24-generic
```

### 7. Обновление зависимостей модулей
```bash
sudo depmod -a 6.14.0-24-generic
```

### 8. Проверка установки
```bash
# Проверка статуса DKMS
sudo dkms status | grep igc

# Проверка наличия модуля
find /lib/modules/*/updates/dkms/ -name "igc.ko"
```

## Важные замечания

1. **Несоответствие версий ядра**: В данном случае система работает с ядром 6.12.8+, но заголовки установлены для 6.14.0-24-generic. Это может быть связано с работой в контейнере или виртуальной среде.

2. **Перезагрузка**: После установки драйвера рекомендуется перезагрузить систему для применения изменений.

3. **Альтернативный вариант**: Если у вас есть доступ к системе с правильной версией ядра, запустите полный скрипт установки:
```bash
sudo ./scripts/setup_timenic.sh
```

## Результат
Драйвер TimeNIC успешно установлен и готов к использованию после перезагрузки системы.