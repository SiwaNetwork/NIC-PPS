# TimeNIC Manager

Комплексное решение для управления сетевой картой TimeNIC (Intel I226 NIC, TCXO, SMA) с поддержкой CLI, GUI и Web интерфейсов.

## Возможности

- ✅ Генерация 1 Гц (PPS) через SDP0 → SMA1
- ✅ Приём внешнего PPS через SDP1 → SMA2
- ✅ Синхронизация PHC по внешнему сигналу
- ✅ Поддержка PTM (PCIe Time Management)
- ✅ Работа с linuxptp, testptp, ts2phc

## Компоненты

### 1. CLI (Command Line Interface)
- Python-based CLI tool
- Полная поддержка всех функций TimeNIC
- Автоматизация настройки

### 2. GUI (Graphical User Interface)
- Qt-based desktop application
- Визуальный мониторинг состояния
- Графики синхронизации

### 3. Web Interface
- FastAPI backend + React frontend
- REST API для удаленного управления
- Real-time мониторинг через WebSocket

## Установка

```bash
# Клонирование репозитория
git clone https://github.com/your-repo/timenic-manager.git
cd timenic-manager

# Установка зависимостей
sudo ./scripts/install_dependencies.sh

# Установка драйвера
sudo ./scripts/install_driver.sh

# Запуск установщика
sudo ./install.sh
```

## Использование

### CLI
```bash
timenic-cli status
timenic-cli enable-pps-output
timenic-cli sync-external-pps
```

### GUI
```bash
timenic-gui
```

### Web
```bash
timenic-web start
# Откройте http://localhost:8000
```

## Требования

- Ubuntu 24.04
- Intel I226 NIC (TimeNIC PCIe card)
- Python 3.10+
- Root/sudo права для настройки PTP

## Лицензия

MIT License