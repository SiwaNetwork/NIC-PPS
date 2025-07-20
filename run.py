#!/usr/bin/env python3
"""
Главный скрипт для запуска Intel NIC PPS Configuration and Monitoring Tool
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path


def check_dependencies():
    """Проверка зависимостей"""
    required_modules = [
        'PyQt6', 'Flask', 'click', 'rich', 'psutil', 'netifaces'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"Ошибка: Отсутствуют необходимые модули: {', '.join(missing_modules)}")
        print("Установите зависимости: pip install -r requirements.txt")
        return False
    
    return True


def check_permissions():
    """Проверка прав доступа"""
    if os.geteuid() != 0:
        print("Предупреждение: Для полной функциональности требуются права root")
        print("Некоторые операции могут не работать без прав администратора")
        return False
    return True


def run_gui():
    """Запуск GUI интерфейса"""
    print("Запуск GUI интерфейса...")
    try:
        subprocess.run([sys.executable, "gui/main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка запуска GUI: {e}")
        return False
    return True


def run_cli(args):
    """Запуск CLI интерфейса"""
    print("Запуск CLI интерфейса...")
    try:
        cli_args = ["cli/main.py"] + args
        subprocess.run([sys.executable] + cli_args, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка запуска CLI: {e}")
        return False
    return True


def run_web():
    """Запуск WEB интерфейса"""
    print("Запуск WEB интерфейса...")
    print("Откройте браузер и перейдите по адресу: http://localhost:5000")
    try:
        subprocess.run([sys.executable, "web/app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка запуска WEB: {e}")
        return False
    return True


def show_help():
    """Показать справку"""
    help_text = """
Intel NIC PPS Configuration and Monitoring Tool

Использование:
    python run.py [опции] [команда]

Опции:
    --gui              Запустить GUI интерфейс
    --cli [аргументы]  Запустить CLI интерфейс
    --web              Запустить WEB интерфейс
    --check            Проверить систему
    --help             Показать эту справку

Примеры:
    python run.py --gui
    python run.py --cli list-nics
    python run.py --cli monitor eth0 --interval 1
    python run.py --web

CLI команды:
    list-nics          Список всех NIC карт
    info <interface>   Информация о карте
    set-pps <interface> --mode <mode>  Установка PPS режима
    set-tcxo <interface> --enable/--disable  Управление TCXO
    monitor <interface> --interval <sec>  Мониторинг
    status             Общий статус
    config --output <file>  Сохранение конфигурации
    config --config <file>   Загрузка конфигурации
    """
    print(help_text)


def check_system():
    """Проверка системы"""
    print("Проверка системы...")
    
    # Проверка зависимостей
    if not check_dependencies():
        return False
    
    # Проверка прав
    check_permissions()
    
    # Проверка наличия Intel NIC карт
    try:
        from core.nic_manager import IntelNICManager
        nic_manager = IntelNICManager()
        nics = nic_manager.get_all_nics()
        
        if nics:
            print(f"✓ Обнаружено Intel NIC карт: {len(nics)}")
            for nic in nics:
                print(f"  - {nic.name}: {nic.mac_address}")
        else:
            print("⚠ Intel NIC карты не обнаружены")
            print("  Убедитесь, что у вас установлены Intel сетевые карты")
            print("  и загружены соответствующие драйверы")
    except Exception as e:
        print(f"✗ Ошибка при проверке NIC карт: {e}")
        return False
    
    # Проверка поддержки PPS
    try:
        result = subprocess.run(["ethtool", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ ethtool доступен")
        else:
            print("⚠ ethtool не найден")
    except FileNotFoundError:
        print("⚠ ethtool не установлен")
    
    print("Проверка завершена")
    return True


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="Intel NIC PPS Configuration and Monitoring Tool",
        add_help=False
    )
    parser.add_argument('--gui', action='store_true', help='Запустить GUI')
    parser.add_argument('--cli', nargs='*', help='Запустить CLI с аргументами')
    parser.add_argument('--web', action='store_true', help='Запустить WEB')
    parser.add_argument('--check', action='store_true', help='Проверить систему')
    parser.add_argument('--help', action='store_true', help='Показать справку')
    
    args = parser.parse_args()
    
    # Показать справку
    if args.help or len(sys.argv) == 1:
        show_help()
        return
    
    # Проверка системы
    if args.check:
        check_system()
        return
    
    # Проверка зависимостей
    if not check_dependencies():
        sys.exit(1)
    
    # Запуск интерфейсов
    success = True
    
    if args.gui:
        success = run_gui()
    elif args.cli is not None:
        success = run_cli(args.cli)
    elif args.web:
        success = run_web()
    else:
        show_help()
        return
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()