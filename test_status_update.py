#!/usr/bin/env python3
"""
Тест обновления статусов в GUI
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from core.nic_manager import IntelNICManager, PPSMode

def test_status_update():
    """Тест обновления статусов"""
    print("🔧 Тестирование обновления статусов...")
    
    nic_manager = IntelNICManager()
    
    # Получаем список NIC
    nics = nic_manager.get_all_nics()
    if not nics:
        print("❌ Нет доступных NIC карт")
        return
    
    test_nic = nics[0]
    print(f"📡 Тестируем NIC: {test_nic.name}")
    print(f"   Текущий PPS режим: {test_nic.pps_mode.value}")
    print(f"   TCXO: {'Включен' if test_nic.tcxo_enabled else 'Отключен'}")
    
    # Тест 1: Изменение PPS режима
    print("\n🔄 Тест 1: Изменение PPS режима")
    
    # Сохраняем исходный режим
    original_pps = test_nic.pps_mode
    
    # Пробуем разные режимы
    test_modes = [PPSMode.OUTPUT, PPSMode.DISABLED, PPSMode.INPUT, original_pps]
    
    for mode in test_modes:
        print(f"   Устанавливаем PPS режим: {mode.value}")
        success = nic_manager.set_pps_mode(test_nic.name, mode)
        
        if success:
            # Получаем обновленную информацию
            updated_nic = nic_manager.get_nic_by_name(test_nic.name)
            if updated_nic:
                print(f"   ✅ PPS режим обновлен: {updated_nic.pps_mode.value}")
                if updated_nic.pps_mode == mode:
                    print(f"   ✅ Статус корректно обновлен!")
                else:
                    print(f"   ❌ Статус не обновлен! Ожидалось: {mode.value}, получено: {updated_nic.pps_mode.value}")
            else:
                print(f"   ❌ Не удалось получить обновленную информацию")
        else:
            print(f"   ❌ Не удалось установить PPS режим: {mode.value}")
    
    # Тест 2: Изменение TCXO
    print("\n🔄 Тест 2: Изменение TCXO")
    
    # Сохраняем исходное состояние
    original_tcxo = test_nic.tcxo_enabled
    
    # Пробуем включить/выключить TCXO
    for enabled in [True, False, original_tcxo]:
        print(f"   Устанавливаем TCXO: {'Включен' if enabled else 'Отключен'}")
        success = nic_manager.set_tcxo_enabled(test_nic.name, enabled)
        
        if success:
            # Получаем обновленную информацию
            updated_nic = nic_manager.get_nic_by_name(test_nic.name)
            if updated_nic:
                print(f"   ✅ TCXO обновлен: {'Включен' if updated_nic.tcxo_enabled else 'Отключен'}")
                if updated_nic.tcxo_enabled == enabled:
                    print(f"   ✅ Статус корректно обновлен!")
                else:
                    print(f"   ❌ Статус не обновлен! Ожидалось: {enabled}, получено: {updated_nic.tcxo_enabled}")
            else:
                print(f"   ❌ Не удалось получить обновленную информацию")
        else:
            print(f"   ❌ Не удалось установить TCXO: {'Включен' if enabled else 'Отключен'}")
    
    print("\n✅ Тест завершен!")

if __name__ == "__main__":
    test_status_update() 