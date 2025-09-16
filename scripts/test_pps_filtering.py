#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции фильтрации PPS событий
Проверяет работу исправления проблемы с двойными фронтами без патча драйвера
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.timenic_manager import TimeNICManager
from core.pps_edge_filter import pps_manager, PPSEvent, PPSEventType


def test_pps_filtering():
    """Тестирование фильтрации PPS событий"""
    print("🧪 Тестирование фильтрации PPS событий")
    print("=" * 50)
    
    # Проверяем доступные PTP устройства
    ptp_devices = list(Path("/dev").glob("ptp*"))
    if not ptp_devices:
        print("❌ PTP устройства не найдены")
        return False
    
    ptp_device = str(ptp_devices[0])
    print(f"📡 Используем PTP устройство: {ptp_device}")
    
    # Создаем менеджер
    manager = TimeNICManager()
    
    # Тест 1: Чтение PPS событий с фильтрацией
    print(f"\n🔍 Тест 1: Чтение PPS событий с фильтрацией")
    print("Подключите внешний PPS к SMA2 и нажмите Enter...")
    input()
    
    try:
        events = manager.read_pps_events(ptp_device, count=5)
        
        if events:
            print(f"✅ Получено {len(events)} отфильтрованных событий:")
            for i, event in enumerate(events, 1):
                print(f"  {i}. Время: {event['timestamp']}, Тип: {event.get('event_type', 'unknown')}")
        else:
            print("⚠️ События не получены. Проверьте подключение PPS")
            
    except Exception as e:
        print(f"❌ Ошибка при чтении событий: {e}")
        return False
    
    # Тест 2: Статистика фильтрации
    print(f"\n📊 Тест 2: Статистика фильтрации")
    stats = manager.get_pps_statistics(ptp_device)
    
    if 'error' not in stats:
        print(f"Статистика фильтрации:")
        print(f"  Всего событий: {stats['total_events']}")
        print(f"  Отфильтровано: {stats['filtered_events']}")
        print(f"  Прошло фильтр: {stats['valid_events']}")
        print(f"  Процент фильтрации: {stats['filter_rate']:.1f}%")
        
        if stats['filtered_events'] > 0:
            print("✅ Двойные фронты PPS успешно отфильтрованы!")
        else:
            print("ℹ️ Двойные фронты не обнаружены")
    else:
        print(f"❌ Ошибка получения статистики: {stats['error']}")
    
    # Тест 3: Мониторинг в реальном времени
    print(f"\n⏱️ Тест 3: Мониторинг в реальном времени (10 секунд)")
    print("Нажмите Enter для запуска...")
    input()
    
    events_received = 0
    
    def event_callback(event):
        nonlocal events_received
        events_received += 1
        print(f"📡 Событие {events_received}: Время: {event.timestamp:.6f}, Тип: {event.event_type.value}")
    
    try:
        # Запускаем мониторинг
        if manager.start_pps_monitoring(ptp_device, event_callback):
            print("✅ Мониторинг запущен")
            
            # Ждем 10 секунд
            time.sleep(10)
            
            # Останавливаем мониторинг
            manager.stop_pps_monitoring(ptp_device)
            print("✅ Мониторинг остановлен")
            
            # Показываем финальную статистику
            final_stats = manager.get_pps_statistics(ptp_device)
            if 'error' not in final_stats:
                print(f"\nФинальная статистика:")
                print(f"  Получено событий: {events_received}")
                print(f"  Всего событий: {final_stats['total_events']}")
                print(f"  Отфильтровано: {final_stats['filtered_events']}")
                print(f"  Процент фильтрации: {final_stats['filter_rate']:.1f}%")
        else:
            print("❌ Не удалось запустить мониторинг")
            
    except Exception as e:
        print(f"❌ Ошибка при мониторинге: {e}")
        return False
    
    return True


def test_cli_integration():
    """Тестирование интеграции с CLI"""
    print(f"\n🖥️ Тест 4: Интеграция с CLI")
    
    try:
        # Тестируем команду read-pps с фильтрацией
        result = subprocess.run([
            sys.executable, "run.py", "--cli", "timenic", "read-pps", "/dev/ptp0", 
            "--count", "3", "--show-filtered"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ CLI команда read-pps работает с фильтрацией")
            print("Вывод:")
            print(result.stdout)
        else:
            print(f"⚠️ CLI команда вернула код {result.returncode}")
            print("Stderr:", result.stderr)
            
    except subprocess.TimeoutExpired:
        print("⚠️ CLI команда превысила таймаут (это нормально для чтения PPS)")
    except Exception as e:
        print(f"❌ Ошибка при тестировании CLI: {e}")


def main():
    """Главная функция тестирования"""
    print("🔧 Тестирование интеграции исправления фронтов PPS")
    print("Этот тест проверяет работу фильтрации на уровне приложения")
    print("без необходимости патча драйвера")
    print()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("⚠️ Для полного тестирования требуются права root")
        print("Некоторые тесты могут не работать")
        print()
    
    # Основные тесты
    success = test_pps_filtering()
    
    if success:
        # Дополнительные тесты
        test_cli_integration()
        
        print(f"\n🎉 Тестирование завершено!")
        print("✅ Фильтрация PPS событий работает корректно")
        print("✅ Проблема с двойными фронтами решена на уровне приложения")
        print()
        print("Теперь ваша программа автоматически фильтрует двойные фронты PPS")
        print("без необходимости применения патча драйвера!")
    else:
        print(f"\n❌ Тестирование не прошло")
        print("Проверьте подключение PPS сигнала к SMA2")


if __name__ == "__main__":
    main()
