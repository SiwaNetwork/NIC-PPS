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
        'PyQt6', 'flask', 'click', 'rich', 'psutil', 'netifaces'
    ]
    
    # TimeNIC specific dependencies
    timenic_modules = [
        'gpiod', 'pyserial'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    # Проверяем TimeNIC модули отдельно
    missing_timenic_modules = []
    for module in timenic_modules:
        try:
            __import__(module)
        except ImportError:
            missing_timenic_modules.append(module)
    
    if missing_modules:
        print(f"Ошибка: Отсутствуют основные модули: {', '.join(missing_modules)}")
        print("Установите зависимости: pip install -r requirements.txt")
        return False
    
    if missing_timenic_modules:
        print(f"Предупреждение: Отсутствуют модули для TimeNIC: {', '.join(missing_timenic_modules)}")
        print("Для полной функциональности TimeNIC установите: pip install gpiod pyserial")
    
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
        # Проверяем, есть ли команда timenic
        if args and args[0] == 'timenic':
            # Запускаем TimeNIC CLI
            cli_args = ["cli/timenic_cli.py"] + args[1:]
            subprocess.run([sys.executable] + cli_args, check=True)
        else:
            # Запускаем обычный CLI
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
Поддержка TimeNIC (Intel I226 NIC, SMA, TCXO)

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
    python run.py --cli timenic list-timenics
    python run.py --cli timenic set-pps enp3s0 --mode output
    python run.py --cli timenic read-pps /dev/ptp0 --count 5
    python run.py --cli timenic set-period /dev/ptp0 --period 1000000000
    python run.py --cli timenic sync-phc enp3s0
    python run.py --cli timenic monitor enp3s0 --interval 1
    python run.py --web

CLI команды (обычные NIC):
    list-nics          Список всех NIC карт
    info <interface>   Информация о карте
    set-pps <interface> --mode <mode>  Установка PPS режима
    monitor <interface> --interval <sec>  Мониторинг
    status             Общий статус

CLI команды (TimeNIC):
    timenic list-timenics    Список всех TimeNIC карт
    timenic info <interface> Информация о TimeNIC карте
    timenic set-pps <interface> --mode <mode>  Установка PPS режима
        Режимы: disabled, input (SMA2), output (SMA1), both
    timenic list-ptp        Список PTP устройств
    timenic read-pps <ptp_device> --count <count>  Чтение PPS событий
        Пример: timenic read-pps /dev/ptp0 --count 5
    timenic set-period <ptp_device> --period <ns>  Установка периода PPS
        Пример: timenic set-period /dev/ptp0 --period 1000000000 (1 Гц)
    timenic sync-phc <interface>  Синхронизация PHC с системным временем
    timenic start-phc-sync <interface>  Запуск синхронизации PHC по внешнему PPS
    timenic enable-ptm <interface>  Включение PTM
    timenic monitor <interface> --interval <sec>  Мониторинг
    timenic create-service  Создание systemd сервиса
    timenic status          Общий статус TimeNIC системы

Настройка TimeNIC по гайду:
    1. Включение PPS выхода на SMA1 (1 Гц):
       python run.py --cli timenic set-pps enp3s0 --mode output
    
    2. Включение PPS входа на SMA2:
       python run.py --cli timenic set-pps enp3s0 --mode input
    
    3. Чтение внешних PPS событий:
       python run.py --cli timenic read-pps /dev/ptp0 --count 5
    
    4. Синхронизация PHC по внешнему PPS:
       python run.py --cli timenic start-phc-sync enp3s0
    
    5. Создание автозапуска:
       sudo python run.py --cli timenic create-service
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
    
    # Проверка TimeNIC карт
    try:
        from core.timenic_manager import TimeNICManager
        timenic_manager = TimeNICManager()
        timenics = timenic_manager.get_all_timenics()
        
        if timenics:
            print(f"✓ Обнаружено TimeNIC карт: {len(timenics)}")
            for timenic in timenics:
                print(f"  - {timenic.name}: {timenic.mac_address} (PTP: {timenic.ptp_device or 'Нет'})")
        else:
            print("⚠ TimeNIC карты не обнаружены")
            print("  Убедитесь, что у вас установлена TimeNIC карта с драйвером igc")
    except Exception as e:
        print(f"✗ Ошибка при проверке TimeNIC карт: {e}")
    
    # Проверка PTP устройств
    try:
        ptp_devices = list(Path("/dev").glob("ptp*"))
        if ptp_devices:
            print(f"✓ Обнаружено PTP устройств: {len(ptp_devices)}")
            for ptp in ptp_devices:
                print(f"  - {ptp}")
        else:
            print("⚠ PTP устройства не обнаружены")
    except Exception as e:
        print(f"✗ Ошибка при проверке PTP устройств: {e}")
    
    # Проверка системных утилит
    timenic_utils = ['testptp', 'ts2phc', 'phc_ctl', 'ethtool']
    for util in timenic_utils:
        try:
            result = subprocess.run([util, "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ {util} доступен")
            else:
                print(f"⚠ {util} не найден")
        except FileNotFoundError:
            print(f"⚠ {util} не установлен")
    
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