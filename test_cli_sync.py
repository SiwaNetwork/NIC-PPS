#!/usr/bin/env python3
"""
Тест CLI команд синхронизации
"""

import subprocess
import sys
import os

def test_cli_commands():
    """Тест CLI команд синхронизации"""
    print("🔧 Тестирование CLI команд синхронизации...")
    
    # Базовые команды
    commands = [
        ["python3", "-m", "cli.main", "list-nics"],
        ["python3", "-m", "cli.main", "status"],
        ["python3", "-m", "cli.main", "sync-status"],
        ["python3", "-m", "cli.main", "stop-phc-sync"],
        ["python3", "-m", "cli.main", "stop-ts2phc-sync"],
        ["python3", "-m", "cli.main", "start-phc-sync", "/dev/ptp2", "/dev/ptp0"],
        ["python3", "-m", "cli.main", "start-ts2phc-sync", "enp3s0", "/dev/ptp0"],
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"\n🔄 Тест {i}: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"✅ Успешно: {result.stdout[:100]}...")
            else:
                print(f"⚠️ Ошибка: {result.stderr[:100]}...")
        except subprocess.TimeoutExpired:
            print("⏰ Таймаут")
        except Exception as e:
            print(f"❌ Исключение: {e}")
    
    print("\n✅ Тест CLI команд завершен!")

if __name__ == "__main__":
    test_cli_commands() 