# SHIWA NIC-PPS Project Structure

**Версия:** 1.1.0  
**Дата сборки:** 2025-09-09  
**Описание:** Исправлено определение PTP устройства для Intel I210

## 🚀 Основные компоненты

### **Запуск приложения:**
- `run.py` - Главный скрипт запуска (GUI/CLI/Web)
- `version.py` - Информация о версии проекта

### **Веб-интерфейс:**
- `web/app.py` - Flask веб-приложение
- `web/templates/index.html` - HTML интерфейс
- `web/static/js/app.js` - JavaScript функциональность

### **CLI интерфейс:**
- `cli/main.py` - Основной CLI для Intel NIC
- `cli/timenic_cli.py` - CLI для TimeNIC карт

### **Ядро системы:**
- `core/nic_manager.py` - Менеджер Intel NIC карт
- `core/timenic_manager.py` - Менеджер TimeNIC карт

### **GUI интерфейс:**
- `gui/main.py` - PyQt6 графический интерфейс

## 🛠️ Утилиты

### **Тестирование и проверка:**
- `check_pps.py` - Проверка PPS сигнала
- `test_pps_signal.py` - Детальное тестирование PPS
- `setup_timenic_full.py` - Полная настройка TimeNIC

### **Конфигурация:**
- `requirements.txt` - Python зависимости
- `LICENSE` - Лицензия проекта

## 📚 Документация

### **Руководства:**
- `docs/README.md` - Основная документация
- `docs/TIMENIC_SETUP.md` - Настройка TimeNIC
- `docs/timenic_pps_commands.md` - Команды PPS

### **Справка:**
- `TROUBLESHOOTING.md` - Решение проблем
- `CHANGELOG.md` - История изменений

## 🎯 Быстрый старт

```bash
# Активация виртуального окружения
source venv/bin/activate

# Запуск веб-интерфейса
python run.py --web

# Запуск CLI
python run.py --cli list-nics

# Запуск GUI
python run.py --gui

# Проверка PPS
python check_pps.py --test
```

## 🌐 Веб-интерфейс

Доступен по адресам:
- http://localhost:5000
- http://192.168.16.173:5000

## ⚡ PPS настройка

**Сетевая карта (/dev/ptp0):**
- SDP0 - PPS выход 1 Гц
- SDP1 - PPS вход

**SMA устройство (/dev/ptp2):**
- SMA1 - PPS выход 1 Гц  
- SMA2 - PPS вход

**PHC синхронизация:**
```bash
sudo phc2sys -s /dev/ptp2 -c /dev/ptp0 -O 0 -R 16 -m
```
