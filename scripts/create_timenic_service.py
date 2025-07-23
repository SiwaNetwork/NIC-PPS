#!/usr/bin/env python3
"""
Скрипт для создания systemd сервиса TimeNIC
Автоматически настраивает PPS при загрузке системы
"""

import os
import sys
import subprocess
from pathlib import Path


SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description=Setup PTP on TimeNIC PCIe card
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes

# Настройка PPS выхода на SMA1 (SDP0)
ExecStart=/usr/bin/testptp -d {ptp_device} -L0,2
ExecStart=/usr/bin/testptp -d {ptp_device} -p 1000000000

# Настройка PPS входа на SMA2 (SDP1)
ExecStart=/usr/bin/testptp -d {ptp_device} -L1,1

# Запуск синхронизации PHC по внешнему PPS (опционально)
{phc_sync_cmd}

[Install]
WantedBy=multi-user.target
"""


def find_ptp_device(interface):
    """Поиск PTP устройства для интерфейса"""
    try:
        result = subprocess.run(
            ["ethtool", "-T", interface],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'PTP Hardware Clock:' in line:
                    clock_id = line.split(':')[1].strip()
                    return f"/dev/ptp{clock_id}"
    except Exception as e:
        print(f"Ошибка при поиске PTP устройства: {e}")
    return None


def create_service(interface=None, enable_phc_sync=False):
    """Создание systemd сервиса"""
    
    # Проверка прав root
    if os.geteuid() != 0:
        print("❌ Этот скрипт должен быть запущен с правами root")
        print("Используйте: sudo python3 create_timenic_service.py")
        sys.exit(1)
    
    # Поиск PTP устройства
    if interface:
        ptp_device = find_ptp_device(interface)
        if not ptp_device:
            print(f"❌ PTP устройство не найдено для интерфейса {interface}")
            sys.exit(1)
    else:
        # Ищем первое доступное PTP устройство
        ptp_devices = list(Path("/dev").glob("ptp*"))
        if not ptp_devices:
            print("❌ PTP устройства не найдены в системе")
            sys.exit(1)
        ptp_device = str(ptp_devices[0])
        print(f"ℹ️  Используется PTP устройство: {ptp_device}")
    
    # Формируем команду синхронизации PHC
    phc_sync_cmd = ""
    if enable_phc_sync:
        phc_sync_cmd = f"ExecStart=/usr/sbin/ts2phc -c {ptp_device} -s generic --ts2phc.pin_index 1 -m -l 7"
    else:
        phc_sync_cmd = "# ExecStart=/usr/sbin/ts2phc -c {ptp_device} -s generic --ts2phc.pin_index 1 -m -l 7"
    
    # Генерируем содержимое сервиса
    service_content = SYSTEMD_SERVICE_TEMPLATE.format(
        ptp_device=ptp_device,
        phc_sync_cmd=phc_sync_cmd
    )
    
    # Путь к файлу сервиса
    service_path = "/etc/systemd/system/ptp-nic-setup.service"
    
    # Записываем файл сервиса
    print(f"📝 Создание сервиса {service_path}...")
    with open(service_path, 'w') as f:
        f.write(service_content)
    
    # Перезагружаем systemd
    print("🔄 Перезагрузка systemd...")
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    
    # Включаем сервис
    print("✅ Включение сервиса...")
    subprocess.run(["systemctl", "enable", "ptp-nic-setup"], check=True)
    
    print("\n✨ Сервис успешно создан!")
    print("\nДоступные команды:")
    print("  sudo systemctl start ptp-nic-setup    # Запустить сервис")
    print("  sudo systemctl status ptp-nic-setup   # Проверить статус")
    print("  sudo systemctl stop ptp-nic-setup     # Остановить сервис")
    print("  sudo journalctl -u ptp-nic-setup      # Просмотр логов")
    
    # Предложение запустить сервис
    response = input("\nЗапустить сервис сейчас? (y/N): ")
    if response.lower() == 'y':
        subprocess.run(["systemctl", "start", "ptp-nic-setup"], check=True)
        print("✅ Сервис запущен")
        
        # Показываем статус
        subprocess.run(["systemctl", "status", "ptp-nic-setup", "--no-pager"])


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Создание systemd сервиса для TimeNIC"
    )
    parser.add_argument(
        '--interface', '-i',
        help='Сетевой интерфейс TimeNIC (например, enp3s0)'
    )
    parser.add_argument(
        '--enable-phc-sync',
        action='store_true',
        help='Включить синхронизацию PHC по внешнему PPS'
    )
    
    args = parser.parse_args()
    
    create_service(args.interface, args.enable_phc_sync)


if __name__ == "__main__":
    main()