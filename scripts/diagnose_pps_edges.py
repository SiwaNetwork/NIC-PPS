#!/usr/bin/env python3
"""
Скрипт для диагностики проблемы с фронтами PPS
Помогает выявить, почему задний фронт PPS NIC карты привязывается к переднему фронту основных часов
"""

import subprocess
import os
import sys
import time
from pathlib import Path

def check_ptp_devices():
    """Проверка доступных PTP устройств"""
    print("🔍 Проверка PTP устройств...")
    ptp_devices = list(Path("/dev").glob("ptp*"))
    
    if not ptp_devices:
        print("❌ PTP устройства не найдены")
        return []
    
    print(f"✅ Найдено PTP устройств: {len(ptp_devices)}")
    for device in ptp_devices:
        print(f"  - {device}")
    
    return [str(d) for d in ptp_devices]

def check_pps_configuration(ptp_device):
    """Проверка конфигурации PPS для устройства"""
    print(f"\n🔧 Проверка конфигурации PPS для {ptp_device}...")
    
    try:
        # Получаем текущую конфигурацию
        result = subprocess.run(
            ["testptp", "-d", ptp_device, "-l"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Текущая конфигурация:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f"  {line}")
        else:
            print(f"❌ Ошибка получения конфигурации: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Исключение при проверке конфигурации: {e}")

def test_pps_events(ptp_device, count=10):
    """Тестирование PPS событий для выявления двойных фронтов"""
    print(f"\n📊 Тестирование PPS событий для {ptp_device} (событий: {count})...")
    
    try:
        # Читаем события
        result = subprocess.run(
            ["testptp", "-d", ptp_device, "-e", str(count)],
            capture_output=True, text=True, timeout=count + 5
        )
        
        if result.returncode == 0:
            events = []
            for line in result.stdout.split('\n'):
                if 'event' in line and 'index' in line:
                    events.append(line.strip())
            
            print(f"Получено событий: {len(events)}")
            
            # Анализируем интервалы между событиями
            if len(events) > 1:
                print("\nАнализ интервалов между событиями:")
                timestamps = []
                for event in events:
                    # Извлекаем временную метку
                    parts = event.split()
                    if len(parts) >= 6:
                        timestamp = float(parts[4])
                        timestamps.append(timestamp)
                
                if len(timestamps) > 1:
                    intervals = []
                    for i in range(1, len(timestamps)):
                        interval = timestamps[i] - timestamps[i-1]
                        intervals.append(interval)
                    
                    print(f"Интервалы между событиями (сек):")
                    for i, interval in enumerate(intervals):
                        print(f"  Событие {i+1}-{i+2}: {interval:.6f} сек")
                    
                    # Проверяем на двойные события
                    short_intervals = [i for i in intervals if i < 0.5]  # Меньше 0.5 сек
                    if short_intervals:
                        print(f"⚠️  Обнаружены короткие интервалы: {len(short_intervals)}")
                        print("   Это может указывать на двойные события от обоих фронтов")
                    else:
                        print("✅ Интервалы выглядят нормально (~1 сек)")
            
            # Показываем все события
            print(f"\nВсе события:")
            for i, event in enumerate(events):
                print(f"  {i+1}: {event}")
                
        else:
            print(f"❌ Ошибка чтения событий: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Исключение при тестировании событий: {e}")

def check_driver_info():
    """Проверка информации о драйвере"""
    print(f"\n🔍 Проверка драйвера igc...")
    
    try:
        # Проверяем загружен ли драйвер
        result = subprocess.run(
            ["lsmod"], capture_output=True, text=True
        )
        
        if result.returncode == 0:
            if 'igc' in result.stdout:
                print("✅ Драйвер igc загружен")
            else:
                print("❌ Драйвер igc не загружен")
        
        # Проверяем версию драйвера
        result = subprocess.run(
            ["modinfo", "igc"], capture_output=True, text=True
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'version:' in line.lower():
                    print(f"  Версия драйвера: {line.strip()}")
                elif 'filename:' in line.lower():
                    print(f"  Путь к драйверу: {line.strip()}")
                    
    except Exception as e:
        print(f"❌ Ошибка при проверке драйвера: {e}")

def check_sysfs_interface(ptp_device):
    """Проверка sysfs интерфейса для настройки фронтов"""
    print(f"\n🔧 Проверка sysfs интерфейса для {ptp_device}...")
    
    ptp_num = ptp_device.split('/dev/ptp')[1] if '/dev/ptp' in ptp_device else '0'
    sysfs_path = f"/sys/class/ptp/ptp{ptp_num}"
    
    if os.path.exists(sysfs_path):
        print(f"✅ Sysfs интерфейс найден: {sysfs_path}")
        
        # Проверяем доступные файлы
        try:
            files = os.listdir(sysfs_path)
            print("Доступные файлы:")
            for file in sorted(files):
                file_path = os.path.join(sysfs_path, file)
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read().strip()
                        print(f"  {file}: {content}")
                    except:
                        print(f"  {file}: (не удалось прочитать)")
        except Exception as e:
            print(f"❌ Ошибка при чтении sysfs: {e}")
    else:
        print(f"❌ Sysfs интерфейс не найден: {sysfs_path}")

def provide_recommendations():
    """Предоставление рекомендаций по решению проблемы"""
    print(f"\n💡 Рекомендации по решению проблемы с фронтами PPS:")
    print()
    print("1. 🔧 Модификация драйвера igc:")
    print("   - Отредактируйте файл: /usr/src/linux/drivers/net/ethernet/intel/igc/igc_ptp.c")
    print("   - Найдите строку: cfg.extts.flags = RISING_EDGE;")
    print("   - Убедитесь, что используется только RISING_EDGE")
    print("   - Пересоберите драйвер и перезагрузитесь")
    print()
    print("2. ⚙️ Настройка ts2phc:")
    print("   - Используйте параметр --ts2phc.rising_edge")
    print("   - Это заставляет ts2phc использовать только восходящий фронт")
    print()
    print("3. 🔍 Альтернативные решения:")
    print("   - Используйте фильтрацию событий в приложении")
    print("   - Настройте задержку между событиями")
    print("   - Рассмотрите использование другого PTP устройства")
    print()
    print("4. 📊 Мониторинг:")
    print("   - Регулярно проверяйте интервалы между PPS событиями")
    print("   - Используйте этот скрипт для диагностики")

def main():
    """Главная функция"""
    print("🔍 Диагностика проблемы с фронтами PPS")
    print("=" * 50)
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("⚠️  Для полной диагностики требуются права root")
        print("   Некоторые проверки могут не работать")
        print()
    
    # Проверяем доступность testptp
    try:
        subprocess.run(["testptp", "--help"], capture_output=True, timeout=5)
    except:
        print("❌ testptp не найден. Установите linuxptp пакет")
        return
    
    # Основные проверки
    ptp_devices = check_ptp_devices()
    check_driver_info()
    
    if ptp_devices:
        # Тестируем первое доступное устройство
        test_device = ptp_devices[0]
        check_pps_configuration(test_device)
        check_sysfs_interface(test_device)
        test_pps_events(test_device, 10)
    
    provide_recommendations()
    
    print(f"\n✅ Диагностика завершена")

if __name__ == "__main__":
    main()
