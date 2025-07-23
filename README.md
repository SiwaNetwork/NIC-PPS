# Intel IGC Driver с исправлением PPS

Этот репозиторий содержит драйвер Intel IGC для сетевых контроллеров Intel I225-LM/I225-V с исправлением для корректной работы PPS (Pulse Per Second).

## Быстрая установка

Для автоматической установки используйте готовый скрипт:

```bash
sudo ./install_igc_driver.sh
```

Скрипт автоматически:
- Определит ваш дистрибутив Linux
- Установит необходимые зависимости
- Скачает драйвер из официального репозитория
- Соберёт и установит модуль через DKMS
- Настроит автозагрузку

## Ручная установка

Подробная инструкция по ручной установке находится в файле [INSTALLATION_GUIDE_RU.md](INSTALLATION_GUIDE_RU.md)

## Файлы в репозитории

- `intel-igc-ppsfix/` - Исходный код драйвера (распакован из архива)
- `intel-igc-ppsfix_ubuntu.zip` - Оригинальный архив с драйвером
- `install_igc_driver.sh` - Скрипт автоматической установки
- `INSTALLATION_GUIDE_RU.md` - Подробная инструкция на русском языке
- `README.md` - Этот файл

## Проверка работы

После установки проверьте:

1. Статус драйвера:
```bash
sudo dkms status | grep igc
```

2. Загрузку модуля:
```bash
lsmod | grep igc
```

3. Работу PPS (если подключено оборудование):
```bash
sudo ppstest /dev/pps0
```

## Поддерживаемое оборудование

- Intel I225-LM 2.5G Ethernet Controller
- Intel I225-V 2.5G Ethernet Controller

## Требования

- Linux kernel 5.4 или выше
- DKMS (Dynamic Kernel Module Support)
- Компилятор GCC и заголовочные файлы ядра

## Источник

Драйвер взят из репозитория Time Appliances Project:
https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip