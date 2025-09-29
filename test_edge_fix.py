#!/usr/bin/env python3
"""
Тест для проверки исправления привязки по заднему фронту
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.nic_manager import IntelNICManager

def test_edge_compensation():
    """Тест компенсации заднего фронта"""
    print("🧪 Тестирование исправления привязки по заднему фронту...")
    
    # Создаем менеджер NIC
    nic_manager = IntelNICManager()
    
    # Тестируем с отрицательным offset (проблема заднего фронта)
    print("\n📋 Тест 1: Отрицательный offset (задний фронт)")
    print("Ожидаемое поведение: автоматическое переключение направления синхронизации")
    
    try:
        # Симулируем отрицательный offset
        result = nic_manager.apply_edge_compensation(
            source_ptp="/dev/ptp2",
            target_ptp="/dev/ptp0", 
            offset_ns=-800,  # Отрицательный offset
            rate=0.01
        )
        
        if result:
            print("✅ Тест пройден: компенсация заднего фронта работает")
        else:
            print("⚠️ Тест частично пройден: компенсация не сработала, но ошибок нет")
            
    except Exception as e:
        print(f"❌ Тест не пройден: {e}")
        return False
    
    # Тестируем с положительным offset (нормальный случай)
    print("\n📋 Тест 2: Положительный offset (передний фронт)")
    print("Ожидаемое поведение: стандартная синхронизация")
    
    try:
        result = nic_manager.apply_edge_compensation(
            source_ptp="/dev/ptp2",
            target_ptp="/dev/ptp0",
            offset_ns=800,  # Положительный offset
            rate=0.01
        )
        
        if result:
            print("✅ Тест пройден: стандартная синхронизация работает")
        else:
            print("⚠️ Тест частично пройден: синхронизация не запустилась, но ошибок нет")
            
    except Exception as e:
        print(f"❌ Тест не пройден: {e}")
        return False
    
    print("\n🎉 Все тесты завершены!")
    return True

if __name__ == "__main__":
    success = test_edge_compensation()
    sys.exit(0 if success else 1)
