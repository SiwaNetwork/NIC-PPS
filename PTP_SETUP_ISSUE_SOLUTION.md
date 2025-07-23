# Решение проблемы с systemd сервисом PTP

## Проблема

При попытке создания systemd сервиса `ptp-nic-setup.service` возникла ошибка:
```
Job for ptp-nic-setup.service failed because the control process exited with error code.
```

## Причина

1. **Ограниченные возможности PTP устройства**: Текущее PTP устройство (`/dev/ptp0`) имеет очень ограниченные возможности:
   - 0 программируемых пинов
   - 0 каналов внешних временных меток
   - 0 программируемых периодических сигналов

2. **Несовместимость команд**: Systemd сервис пытался выполнить команды настройки пинов, которые не поддерживаются данным устройством:
   ```bash
   testptp -d /dev/ptp0 -L0,2  # Настройка пина 0 - не поддерживается
   testptp -d /dev/ptp0 -p 1000000000  # Периодический сигнал - не поддерживается
   testptp -d /dev/ptp0 -L1,1  # Настройка пина 1 - не поддерживается
   ```

## Решение

### 1. Установка необходимых утилит
```bash
# Установка testptp
sudo bash scripts/install_testptp.sh

# Установка linuxptp (включает ts2phc)
sudo apt-get update && sudo apt-get install -y linuxptp
```

### 2. Использование упрощенного скрипта
Создан скрипт `scripts/ptp-nic-setup-simple.sh`, который:
- Проверяет наличие PTP устройства
- Показывает его возможности
- Выполняет базовую синхронизацию времени

Запуск:
```bash
sudo scripts/ptp-nic-setup-simple.sh
```

### 3. Для реальной карты TimeNIC
Если у вас есть реальная карта TimeNIC с поддержкой всех функций, используйте полный скрипт:
```bash
sudo scripts/ptp-nic-setup.sh
```

## Альтернативные решения

### Запуск без systemd
В контейнерных средах или системах без systemd можно запускать настройку напрямую:
```bash
# Базовая проверка
sudo testptp -d /dev/ptp0 -c

# Синхронизация времени
sudo testptp -d /dev/ptp0 -s

# Получение времени
sudo testptp -d /dev/ptp0 -g
```

### Создание systemd сервиса вручную (для систем с systemd)
Если у вас есть systemd и реальная карта TimeNIC:
```bash
sudo nano /etc/systemd/system/ptp-nic-setup.service
```

Содержимое файла:
```ini
[Unit]
Description=Setup PTP on TimeNIC PCIe card
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes

ExecStart=/usr/bin/testptp -d /dev/ptp0 -L0,2
ExecStart=/usr/bin/testptp -d /dev/ptp0 -p 1000000000
ExecStart=/usr/bin/testptp -d /dev/ptp0 -L1,1
ExecStart=/usr/sbin/ts2phc -c /dev/ptp0 -s generic --ts2phc.pin_index 1 -m -l 7

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ptp-nic-setup
sudo systemctl start ptp-nic-setup
```

## Проверка статуса

### Для виртуального/ограниченного PTP устройства:
```bash
sudo testptp -d /dev/ptp0 -c  # Показать возможности
sudo testptp -d /dev/ptp0 -g  # Показать время
```

### Для реальной карты TimeNIC:
```bash
sudo systemctl status ptp-nic-setup  # Статус сервиса
sudo journalctl -xeu ptp-nic-setup  # Логи сервиса
```

## Заключение

Текущее PTP устройство является виртуальным или имеет ограниченную функциональность. Для полноценной работы с TimeNIC требуется реальная PCIe карта с поддержкой программируемых пинов и внешних временных меток.