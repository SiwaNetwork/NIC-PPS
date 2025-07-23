# Инструкция по установке драйвера Intel IGC с исправлением PPS

Этот драйвер предназначен для сетевых контроллеров Intel I225-LM/I225-V 2.5G Ethernet с исправлением для работы PPS (Pulse Per Second).

## Системные требования

- Linux kernel 5.4 или выше
- DKMS (Dynamic Kernel Module Support)
- Компилятор GCC и заголовочные файлы ядра
- Права суперпользователя (sudo)

## Подготовка системы

### 1. Установка необходимых пакетов

Для Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y dkms build-essential linux-headers-$(uname -r) git wget unzip
```

Для RHEL/CentOS/Fedora:
```bash
sudo yum install -y dkms gcc make kernel-devel-$(uname -r) git wget unzip
# или для новых версий:
sudo dnf install -y dkms gcc make kernel-devel-$(uname -r) git wget unzip
```

### 2. Проверка установки DKMS

```bash
dkms --version
```

Если DKMS не установлен, установите его согласно инструкциям выше.

## Установка драйвера

### Вариант 1: Установка из архива (рекомендуется)

1. Скачайте архив с драйвером:
```bash
cd /tmp
wget https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip
```

2. Распакуйте архив:
```bash
unzip intel-igc-ppsfix_ubuntu.zip
cd intel-igc-ppsfix
```

3. Добавьте драйвер в DKMS:
```bash
sudo dkms add .
```

4. Соберите модуль:
```bash
sudo dkms build igc -v 5.4.0-7642.46
```

5. Установите модуль:
```bash
sudo dkms install --force igc -v 5.4.0-7642.46
```

### Вариант 2: Установка из git-репозитория

1. Клонируйте репозиторий:
```bash
cd /tmp
git clone https://github.com/jksinton/intel-igc.git
cd intel-igc
```

2. Выполните шаги 3-5 из варианта 1.

## Проверка установки

### 1. Проверьте статус модуля в DKMS:
```bash
sudo dkms status | grep igc
```

Вы должны увидеть что-то вроде:
```
igc/5.4.0-7642.46, 6.12.8+, x86_64: installed
```

### 2. Проверьте загрузку модуля:
```bash
lsmod | grep igc
```

### 3. Проверьте сетевые интерфейсы:
```bash
ip link show
# или
ifconfig -a
```

### 4. Проверьте логи системы:
```bash
sudo dmesg | grep igc
```

## Настройка PPS

После установки драйвера, для работы с PPS:

1. Проверьте наличие устройств PPS:
```bash
ls -la /dev/pps*
```

2. Установите утилиты для работы с PPS (если еще не установлены):
```bash
sudo apt install -y pps-tools  # для Ubuntu/Debian
# или
sudo yum install -y pps-tools  # для RHEL/CentOS
```

3. Проверьте работу PPS:
```bash
sudo ppstest /dev/pps0
```

## Удаление драйвера

Если необходимо удалить драйвер:

```bash
sudo dkms remove igc/5.4.0-7642.46 --all
sudo modprobe -r igc
```

## Возможные проблемы и решения

### Проблема 1: Ошибка компиляции
Если возникает ошибка при сборке модуля, убедитесь что:
- Установлены заголовочные файлы ядра для вашей версии
- Версия GCC совместима с вашим ядром

### Проблема 2: Модуль не загружается
1. Проверьте, не загружен ли стандартный модуль igc:
```bash
sudo modprobe -r igc
```

2. Загрузите новый модуль вручную:
```bash
sudo modprobe igc
```

### Проблема 3: Сетевой интерфейс не появляется
1. Проверьте совместимость вашего оборудования:
```bash
lspci | grep -i ethernet
```

2. Убедитесь, что у вас контроллер Intel I225-LM или I225-V

## Автоматическая загрузка при старте системы

Модуль должен загружаться автоматически благодаря параметру `AUTOINSTALL=yes` в конфигурации DKMS. Если этого не происходит:

1. Добавьте модуль в автозагрузку:
```bash
echo "igc" | sudo tee -a /etc/modules
```

2. Обновите initramfs:
```bash
sudo update-initramfs -u
```

## Дополнительная информация

- Версия драйвера: 5.4.0-7642.46
- Поддерживаемое оборудование: Intel I225-LM/I225-V 2.5G Ethernet Controller
- Особенность: Включает исправление для корректной работы PPS (Pulse Per Second)

При возникновении проблем проверьте логи:
```bash
sudo journalctl -xe
sudo dmesg | tail -50
```