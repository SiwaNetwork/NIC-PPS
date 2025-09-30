#!/usr/bin/env python3
"""
Скрипт для проверки привязки PPS к переднему фронту и стабильности phc2sys
"""

import subprocess
import time
import os
import sys

def check_phc2sys_running():
    """Проверка что phc2sys работает"""
    try:
        result = subprocess.run(["pgrep", "-f", "phc2sys"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"✅ phc2sys работает (PID: {', '.join(pids)})")
            return True, pids
        else:
            print("❌ phc2sys не запущен")
            return False, []
    except Exception as e:
        print(f"❌ Ошибка проверки phc2sys: {e}")
        return False, []

def check_pps_edge_binding():
    """Проверка привязки PPS к переднему фронту"""
    print("\n🔍 Проверка привязки PPS к переднему фронту...")
    
    # Проверяем конфигурацию пинов
    try:
        result = subprocess.run(["sudo", "testptp", "-d", "/dev/ptp0", "-l"], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("📊 Конфигурация PTP пинов:")
            print(result.stdout)
            
            # Анализируем конфигурацию
            lines = result.stdout.strip().split('\n')
            sdp0_func = None
            sdp1_func = None
            
            for line in lines:
                if 'SDP0' in line and 'func' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'func':
                            sdp0_func = parts[i+1]
                            break
                elif 'SDP1' in line and 'func' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'func':
                            sdp1_func = parts[i+1]
                            break
            
            print(f"\n📌 SDP0 (output): func={sdp0_func}")
            print(f"📌 SDP1 (input): func={sdp1_func}")
            
            # Проверяем правильность конфигурации
            if sdp0_func == '2' and sdp1_func == '1':
                print("✅ PPS конфигурация правильная:")
                print("   - SDP0 настроен как выход (func=2)")
                print("   - SDP1 настроен как вход (func=1)")
                return True
            else:
                print("❌ Неправильная PPS конфигурация:")
                print(f"   - SDP0 должен быть func=2, получен {sdp0_func}")
                print(f"   - SDP1 должен быть func=1, получен {sdp1_func}")
                return False
        else:
            print(f"❌ Ошибка получения конфигурации PTP: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки PPS: {e}")
        return False

def check_phc2sys_stability(duration=30):
    """Проверка стабильности phc2sys в течение указанного времени"""
    print(f"\n🔍 Проверка стабильности phc2sys в течение {duration} секунд...")
    
    start_time = time.time()
    check_interval = 5
    checks = 0
    failures = 0
    
    while time.time() - start_time < duration:
        is_running, pids = check_phc2sys_running()
        checks += 1
        
        if not is_running:
            failures += 1
            print(f"⚠️ phc2sys упал на проверке {checks} (время: {time.time() - start_time:.1f}s)")
        
        if failures > 2:
            print(f"❌ phc2sys нестабилен - {failures} падений за {checks} проверок")
            return False
            
        time.sleep(check_interval)
    
    print(f"✅ phc2sys стабилен - {failures} падений за {checks} проверок")
    return failures == 0

def check_pps_signal():
    """Проверка наличия PPS сигнала"""
    print("\n🔍 Проверка PPS сигнала...")
    
    try:
        # Проверяем sysfs для PPS
        pps_paths = [
            "/sys/class/ptp/ptp0/pps_enable",
            "/sys/class/ptp/ptp0/pps_available"
        ]
        
        for path in pps_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        value = f.read().strip()
                        print(f"📊 {path}: {value}")
                except Exception as e:
                    print(f"⚠️ Не удалось прочитать {path}: {e}")
        
        # Проверяем через testptp
        result = subprocess.run(["sudo", "testptp", "-d", "/dev/ptp0", "-g"], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("📊 PPS статус через testptp:")
            print(result.stdout)
        else:
            print(f"⚠️ Ошибка получения PPS статуса: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Ошибка проверки PPS сигнала: {e}")

def main():
    print("🔍 Диагностика PPS и phc2sys")
    print("=" * 50)
    
    # 1. Проверяем что phc2sys запущен
    print("\n1️⃣ Проверка запуска phc2sys...")
    is_running, pids = check_phc2sys_running()
    
    if not is_running:
        print("❌ phc2sys не запущен. Запустите синхронизацию в GUI.")
        return False
    
    # 2. Проверяем привязку к переднему фронту
    print("\n2️⃣ Проверка привязки к переднему фронту...")
    edge_ok = check_pps_edge_binding()
    
    # 3. Проверяем PPS сигнал
    print("\n3️⃣ Проверка PPS сигнала...")
    check_pps_signal()
    
    # 4. Проверяем стабильность
    print("\n4️⃣ Проверка стабильности phc2sys...")
    stability_ok = check_phc2sys_stability(30)
    
    # Итоговый результат
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ:")
    print(f"   phc2sys запущен: {'✅' if is_running else '❌'}")
    print(f"   Привязка к переднему фронту: {'✅' if edge_ok else '❌'}")
    print(f"   Стабильность phc2sys: {'✅' if stability_ok else '❌'}")
    
    if is_running and edge_ok and stability_ok:
        print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("\n⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ - требуется исправление")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
