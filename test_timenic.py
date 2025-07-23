#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функций TimeNIC
"""

import sys
import subprocess
from pathlib import Path


def test_imports():
    """Тест импорта модулей"""
    print("🧪 Тестирование импорта модулей...")
    try:
        from core.timenic_manager import TimeNICManager, PPSMode, PTMStatus
        print("✅ core.timenic_manager импортирован успешно")
        
        from cli.timenic_cli import timenic
        print("✅ cli.timenic_cli импортирован успешно")
        
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False


def test_ptp_devices():
    """Тест обнаружения PTP устройств"""
    print("\n🧪 Тестирование PTP устройств...")
    
    ptp_devices = list(Path("/dev").glob("ptp*"))
    if ptp_devices:
        print(f"✅ Найдено PTP устройств: {len(ptp_devices)}")
        for ptp in ptp_devices:
            print(f"   - {ptp}")
    else:
        print("⚠️  PTP устройства не найдены")
    
    return len(ptp_devices) > 0


def test_testptp():
    """Тест наличия testptp"""
    print("\n🧪 Тестирование testptp...")
    
    try:
        result = subprocess.run(["which", "testptp"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ testptp найден: {result.stdout.strip()}")
            return True
        else:
            print("❌ testptp не установлен")
            print("   Выполните: sudo bash scripts/install_testptp.sh")
            return False
    except Exception as e:
        print(f"❌ Ошибка при проверке testptp: {e}")
        return False


def test_network_interfaces():
    """Тест сетевых интерфейсов"""
    print("\n🧪 Тестирование сетевых интерфейсов...")
    
    try:
        result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
        if result.returncode == 0:
            interfaces = []
            for line in result.stdout.split('\n'):
                if ': ' in line and 'lo:' not in line:
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        iface = parts[1].split('@')[0]
                        if iface not in ['lo']:
                            interfaces.append(iface)
            
            if interfaces:
                print(f"✅ Найдено интерфейсов: {len(interfaces)}")
                for iface in interfaces[:5]:  # Показываем первые 5
                    print(f"   - {iface}")
                return True
            else:
                print("⚠️  Сетевые интерфейсы не найдены")
                return False
    except Exception as e:
        print(f"❌ Ошибка при проверке интерфейсов: {e}")
        return False


def test_cli_help():
    """Тест CLI справки"""
    print("\n🧪 Тестирование CLI...")
    
    try:
        result = subprocess.run([sys.executable, "run.py", "--help"], 
                              capture_output=True, text=True)
        if result.returncode == 0 and "TimeNIC" in result.stdout:
            print("✅ CLI работает корректно")
            return True
        else:
            print("❌ Ошибка в CLI")
            return False
    except Exception as e:
        print(f"❌ Ошибка при тестировании CLI: {e}")
        return False


def main():
    """Главная функция тестирования"""
    print("🚀 Запуск тестов TimeNIC...\n")
    
    tests = [
        ("Импорт модулей", test_imports),
        ("PTP устройства", test_ptp_devices),
        ("testptp", test_testptp),
        ("Сетевые интерфейсы", test_network_interfaces),
        ("CLI", test_cli_help)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{name}': {e}")
            results.append((name, False))
    
    # Итоги
    print("\n" + "="*50)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("="*50)
    print(f"Пройдено: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены успешно!")
    else:
        print("\n⚠️  Некоторые тесты не пройдены.")
        print("Проверьте установку зависимостей и наличие оборудования.")


if __name__ == "__main__":
    main()