#!/usr/bin/env python3
"""
Тест функций синхронизации PHC
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from core.nic_manager import IntelNICManager

def test_sync_functions():
    """Тест функций синхронизации"""
    print("🔧 Тестирование функций синхронизации...")
    
    nic_manager = IntelNICManager()
    
    # Получаем список NIC
    nics = nic_manager.get_all_nics()
    if not nics:
        print("❌ Нет доступных NIC карт")
        return
    
    test_nic = nics[0]
    print(f"📡 Тестируем NIC: {test_nic.name}")
    
    # Тест 1: Получение статуса синхронизации
    print("\n🔄 Тест 1: Получение статуса синхронизации")
    status = nic_manager.get_sync_status()
    print(f"   PHC2SYS запущен: {status['phc2sys_running']}")
    print(f"   TS2PHC запущен: {status['ts2phc_running']}")
    print(f"   PHC2SYS PID: {status['phc2sys_pid']}")
    print(f"   TS2PHC PID: {status['ts2phc_pid']}")
    
    # Тест 2: Остановка синхронизации (если запущена)
    print("\n🔄 Тест 2: Остановка синхронизации")
    phc_stop_success = nic_manager.stop_phc_sync()
    ts2phc_stop_success = nic_manager.stop_ts2phc_sync()
    print(f"   Остановка PHC2SYS: {'✅' if phc_stop_success else '❌'}")
    print(f"   Остановка TS2PHC: {'✅' if ts2phc_stop_success else '❌'}")
    
    # Тест 3: Запуск PHC2SYS синхронизации
    print("\n🔄 Тест 3: Запуск PHC2SYS синхронизации")
    print("   Источник: /dev/ptp2, Цель: /dev/ptp0")
    phc_success = nic_manager.start_phc_sync("/dev/ptp2", "/dev/ptp0")
    print(f"   Запуск PHC2SYS: {'✅' if phc_success else '❌'}")
    
    # Проверяем статус после запуска
    status = nic_manager.get_sync_status()
    print(f"   PHC2SYS запущен: {status['phc2sys_running']}")
    
    # Тест 4: Запуск TS2PHC синхронизации
    print("\n🔄 Тест 4: Запуск TS2PHC синхронизации")
    print(f"   NIC: {test_nic.name}, PTP устройство: /dev/ptp0")
    ts2phc_success = nic_manager.start_ts2phc_sync(test_nic.name, "/dev/ptp0")
    print(f"   Запуск TS2PHC: {'✅' if ts2phc_success else '❌'}")
    
    # Проверяем статус после запуска
    status = nic_manager.get_sync_status()
    print(f"   TS2PHC запущен: {status['ts2phc_running']}")
    
    # Тест 5: Остановка синхронизации
    print("\n🔄 Тест 5: Остановка синхронизации")
    phc_stop_success = nic_manager.stop_phc_sync()
    ts2phc_stop_success = nic_manager.stop_ts2phc_sync()
    print(f"   Остановка PHC2SYS: {'✅' if phc_stop_success else '❌'}")
    print(f"   Остановка TS2PHC: {'✅' if ts2phc_stop_success else '❌'}")
    
    # Финальная проверка статуса
    status = nic_manager.get_sync_status()
    print(f"   Финальный статус - PHC2SYS: {status['phc2sys_running']}, TS2PHC: {status['ts2phc_running']}")
    
    print("\n✅ Тест завершен!")

if __name__ == "__main__":
    test_sync_functions() 