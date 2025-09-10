#!/usr/bin/env python3
"""
Скрипт для запуска тестов SHIWA NIC-PPS
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def run_tests(test_type='all', verbose=False, coverage=False):
    """Запуск тестов"""
    
    # Проверяем, что мы в правильной директории
    if not Path('tests').exists():
        print("Ошибка: Директория tests не найдена. Запустите скрипт из корня проекта.")
        return False
    
    # Базовые аргументы pytest
    cmd = ['python', '-m', 'pytest']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=core', '--cov=web', '--cov=monitoring', '--cov-report=html'])
    
    # Выбираем тесты для запуска
    if test_type == 'unit':
        cmd.extend(['tests/test_nic_manager.py', 'tests/test_metrics.py'])
    elif test_type == 'integration':
        cmd.extend(['tests/test_web_app.py'])
    elif test_type == 'all':
        cmd.append('tests/')
    else:
        print(f"Неизвестный тип тестов: {test_type}")
        return False
    
    print(f"Запуск тестов: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ Все тесты прошли успешно!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Тесты завершились с ошибкой (код: {e.returncode})")
        return False
    except FileNotFoundError:
        print("❌ pytest не найден. Установите его: pip install pytest")
        return False

def check_dependencies():
    """Проверка зависимостей для тестирования"""
    required_packages = ['pytest', 'pytest-cov']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Отсутствуют пакеты для тестирования: {', '.join(missing_packages)}")
        print("Установите их: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ Все зависимости для тестирования установлены")
    return True

def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Запуск тестов SHIWA NIC-PPS')
    parser.add_argument('--type', choices=['all', 'unit', 'integration'], 
                       default='all', help='Тип тестов для запуска')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Подробный вывод')
    parser.add_argument('--coverage', '-c', action='store_true', 
                       help='Покрытие кода тестами')
    parser.add_argument('--check-deps', action='store_true', 
                       help='Проверить зависимости')
    
    args = parser.parse_args()
    
    if args.check_deps:
        return check_dependencies()
    
    if not check_dependencies():
        return 1
    
    success = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
