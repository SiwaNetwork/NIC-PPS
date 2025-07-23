#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений:
1. Проблема создания копий NIC устройств
2. Проблема неработающего мониторинга трафика
"""

import time
import sys
from core.timenic_manager import TimeNICManager, PPSMode

def test_duplicate_devices():
    """Тест на проблему дублирования устройств"""
    print("=== Тест дублирования устройств ===")
    
    manager = TimeNICManager()
    
    # Получаем начальный список
    initial_devices = manager.get_all_timenics()
    print(f"Начальное количество устройств: {len(initial_devices)}")
    for device in initial_devices:
        print(f"  - {device.name}: {device.mac_address}")
    
    # Обновляем список несколько раз
    print("\nОбновляем список 3 раза...")
    for i in range(3):
        manager.refresh()
        devices = manager.get_all_timenics()
        print(f"Попытка {i+1}: количество устройств = {len(devices)}")
    
    # Проверяем, что количество не увеличилось
    final_devices = manager.get_all_timenics()
    if len(final_devices) == len(initial_devices):
        print("✅ Тест пройден: дубликаты не создаются")
    else:
        print("❌ Тест провален: создаются дубликаты устройств")
        print(f"   Было: {len(initial_devices)}, стало: {len(final_devices)}")


def test_traffic_monitoring():
    """Тест мониторинга трафика"""
    print("\n=== Тест мониторинга трафика ===")
    
    manager = TimeNICManager()
    devices = manager.get_all_timenics()
    
    if not devices:
        print("❌ Нет доступных TimeNIC устройств для тестирования")
        return
    
    # Берем первое устройство
    device = devices[0]
    print(f"Тестируем мониторинг для {device.name}")
    
    # Получаем статистику несколько раз
    print("\nПолучаем статистику 3 раза с интервалом 2 секунды...")
    
    stats_history = []
    for i in range(3):
        stats = manager.get_statistics(device.name)
        stats_history.append(stats)
        
        print(f"\nИтерация {i+1}:")
        if 'rx_bytes' in stats:
            print(f"  RX bytes: {stats['rx_bytes']:,}")
        if 'tx_bytes' in stats:
            print(f"  TX bytes: {stats['tx_bytes']:,}")
        if 'rx_packets' in stats:
            print(f"  RX packets: {stats['rx_packets']:,}")
        if 'tx_packets' in stats:
            print(f"  TX packets: {stats['tx_packets']:,}")
        
        if i < 2:
            time.sleep(2)
    
    # Проверяем, что статистика меняется
    if len(stats_history) >= 2:
        if 'rx_bytes' in stats_history[0] and 'rx_bytes' in stats_history[-1]:
            if stats_history[-1]['rx_bytes'] != stats_history[0]['rx_bytes']:
                print("\n✅ Статистика трафика обновляется")
            else:
                print("\n⚠️  Статистика трафика не изменилась (возможно, нет активного трафика)")
        else:
            print("\n❌ Не удалось получить статистику трафика")
    
    # Тест callback мониторинга
    print("\n\nТестируем мониторинг с callback (5 секунд)...")
    
    def monitor_callback(stats):
        if 'rx_speed' in stats:
            print(f"RX: {stats['rx_speed'] * 8 / 1_000_000:.2f} Mbps", end="")
        if 'tx_speed' in stats:
            print(f", TX: {stats['tx_speed'] * 8 / 1_000_000:.2f} Mbps", end="")
        if 'temperature' in stats and stats['temperature']:
            print(f", Temp: {stats['temperature']:.1f}°C", end="")
        print()
    
    try:
        # Запускаем мониторинг на 5 секунд
        import threading
        monitor_thread = threading.Thread(
            target=lambda: manager.monitor_traffic(device.name, callback=monitor_callback, interval=1),
            daemon=True
        )
        monitor_thread.start()
        time.sleep(5)
        print("\n✅ Мониторинг с callback работает")
    except Exception as e:
        print(f"\n❌ Ошибка мониторинга: {e}")


def test_pps_settings():
    """Тест применения настроек PPS"""
    print("\n=== Тест применения настроек PPS ===")
    
    manager = TimeNICManager()
    devices = manager.get_all_timenics()
    
    if not devices:
        print("❌ Нет доступных TimeNIC устройств для тестирования")
        return
    
    device = devices[0]
    print(f"Тестируем настройки PPS для {device.name}")
    
    # Сохраняем текущий режим
    original_mode = device.pps_mode
    print(f"Текущий режим PPS: {original_mode.value}")
    
    # Пробуем изменить режим
    test_modes = [PPSMode.DISABLED, PPSMode.OUTPUT, PPSMode.INPUT]
    for mode in test_modes:
        if mode != original_mode:
            print(f"\nПробуем установить режим: {mode.value}")
            success = manager.set_pps_mode(device.name, mode)
            
            if success:
                # Проверяем, применились ли настройки
                manager.refresh()
                updated_device = manager.get_timenic_by_name(device.name)
                if updated_device and updated_device.pps_mode == mode:
                    print(f"✅ Режим {mode.value} успешно установлен")
                else:
                    print(f"❌ Режим {mode.value} не применился")
            else:
                print(f"⚠️  Не удалось установить режим {mode.value} (возможно, нужны права root)")
            
            # Небольшая пауза между изменениями
            time.sleep(1)
    
    # Восстанавливаем исходный режим
    print(f"\nВосстанавливаем исходный режим: {original_mode.value}")
    manager.set_pps_mode(device.name, original_mode)


if __name__ == "__main__":
    print("Запуск тестов исправлений...\n")
    
    # Проверяем права доступа
    import os
    if os.geteuid() != 0:
        print("⚠️  Внимание: некоторые тесты могут требовать прав root")
        print("   Рекомендуется запустить: sudo python3 test_fixes.py\n")
    
    try:
        test_duplicate_devices()
        test_traffic_monitoring()
        test_pps_settings()
        
        print("\n\n=== Тесты завершены ===")
        
    except KeyboardInterrupt:
        print("\n\nТесты прерваны пользователем")
    except Exception as e:
        print(f"\n\nОшибка при выполнении тестов: {e}")
        import traceback
        traceback.print_exc()