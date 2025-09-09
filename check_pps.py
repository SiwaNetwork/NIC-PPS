#!/usr/bin/env python3
"""
Скрипт для проверки PPS сигнала
Версия 1.1.0 - Исправлено определение PTP устройства для Intel I210
"""

import subprocess
import time
import sys
import glob

def find_network_interface():
    """Поиск активной сетевой карты"""
    try:
        # Получаем список всех сетевых интерфейсов
        result = subprocess.run(['ip', 'link', 'show'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'enp' in line or 'eno' in line or 'eth' in line:
                    # Извлекаем имя интерфейса
                    parts = line.split(':')
                    if len(parts) >= 2:
                        interface = parts[1].strip()
                        if interface and not interface.startswith('lo'):
                            print(f"Найден сетевой интерфейс: {interface}")
                            return interface
    except Exception as e:
        print(f"Ошибка поиска интерфейса: {e}")
    
    return None

def find_ptp_device_for_interface(interface):
    """Поиск PTP устройства для сетевого интерфейса"""
    try:
        # Используем ethtool для получения PTP clock
        result = subprocess.run(['ethtool', '-T', interface], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'PTP Hardware Clock:' in line:
                    clock_num = line.split(':')[1].strip()
                    ptp_device = f"/dev/ptp{clock_num}"
                    print(f"PTP устройство для {interface}: {ptp_device}")
                    return ptp_device
    except Exception as e:
        print(f"Ошибка поиска PTP устройства: {e}")
    
    # Если не нашли через ethtool, ищем все PTP устройства
    try:
        ptp_devices = glob.glob("/dev/ptp*")
        if ptp_devices:
            # Проверяем каждое PTP устройство
            for ptp_device in sorted(ptp_devices):
                result = subprocess.run(['sudo', 'testptp', '-d', ptp_device, '-l'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Проверяем, есть ли SDP пины (сетевая карта)
                    if 'SDP' in result.stdout:
                        print(f"Найдено PTP устройство с SDP пинами: {ptp_device}")
                        return ptp_device
    except Exception as e:
        print(f"Ошибка поиска PTP устройств: {e}")
    
    return None

def check_pps_status():
    """Проверка статуса PPS"""
    print("=== Проверка PPS статуса ===")
    
    # Находим сетевой интерфейс
    interface = find_network_interface()
    if not interface:
        print("❌ Не найден активный сетевой интерфейс")
        return None
    
    # Находим PTP устройство
    ptp_device = find_ptp_device_for_interface(interface)
    if not ptp_device:
        print("❌ Не найдено PTP устройство")
        return None
    
    print(f"Используем PTP устройство: {ptp_device}")
    
    # Проверяем статус пинов
    try:
        result = subprocess.run(['sudo', 'testptp', '-d', ptp_device, '-l'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("PPS пины:")
            print(result.stdout)
        else:
            print(f"Ошибка проверки пинов: {result.stderr}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Проверяем, что периодический выход активен
    try:
        result = subprocess.run(['sudo', 'testptp', '-d', ptp_device, '-p', '1000000000'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ Периодический выход 1 Гц активен")
        else:
            print(f"✗ Ошибка периодического выхода: {result.stderr}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    return ptp_device

def test_pps_output():
    """Тест PPS выхода"""
    print("\n=== Тест PPS выхода ===")
    
    # Находим PTP устройство
    ptp_device = check_pps_status()
    if not ptp_device:
        print("❌ Не удалось найти PTP устройство")
        return False
    
    # Устанавливаем PPS выход на SDP0 (первый пин)
    try:
        result = subprocess.run(['sudo', 'testptp', '-d', ptp_device, '-L0,2'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ PPS выход настроен на SDP0")
        else:
            print(f"✗ Ошибка настройки PPS выхода: {result.stderr}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Устанавливаем период 1 Гц
    try:
        result = subprocess.run(['sudo', 'testptp', '-d', ptp_device, '-p', '1000000000'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ Период 1 Гц установлен")
        else:
            print(f"✗ Ошибка установки периода: {result.stderr}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Проверяем финальный статус
    try:
        result = subprocess.run(['sudo', 'testptp', '-d', ptp_device, '-l'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("\nФинальный статус пинов:")
            print(result.stdout)
            
            # Проверяем, что SDP0 настроен как выход
            if "SDP0 index 0 func 2" in result.stdout:
                print("✓ PPS выход активен на SDP0 (1 Гц)")
                return True
            else:
                print("✗ PPS выход не активен")
                return False
        else:
            print(f"✗ Ошибка проверки статуса: {result.stderr}")
            return False
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

if __name__ == "__main__":
    print("SHIWA NIC-PPS Проверка")
    print("=" * 30)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        success = test_pps_output()
        if success:
            print("\n🎉 PPS сигнал 1 Гц успешно выдается на SDP0!")
            print("Подключите осциллограф или частотомер к разъему INTEL I210 для проверки.")
        else:
            print("\n❌ PPS сигнал не работает")
            sys.exit(1)
    else:
        ptp_device = check_pps_status()
        if ptp_device:
            print(f"\n✅ PPS настроен на устройстве: {ptp_device}")
            print("Для тестирования PPS выхода запустите:")
            print("python check_pps.py --test")
        else:
            print("\n❌ Не удалось настроить PPS")
            sys.exit(1)
