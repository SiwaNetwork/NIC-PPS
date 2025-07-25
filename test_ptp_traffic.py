#!/usr/bin/env python3
"""
Скрипт для генерации тестового PTP трафика
"""

import socket
import struct
import time
import threading
from datetime import datetime

def create_ptp_packet(ptp_type=0x00, sequence_id=1):
    """Создание тестового PTP пакета"""
    # PTP header (IEEE 1588-2008)
    ptp_header = struct.pack('!BBBBHHHBBBBBBBB',
        0x11,  # Version 2, PTP
        0x02,  # PTP version 2
        0x00,  # Reserved
        0x00,  # Reserved
        0x00,  # Message length
        0x00,  # Domain number
        0x00,  # Reserved
        ptp_type,  # Message type (0x00 = Sync)
        sequence_id,  # Sequence ID
        0x00,  # Control field
        0x00,  # Log message interval
        0x00,  # Reserved
        0x00,  # Reserved
        0x00,  # Reserved
        0x00,  # Reserved
        0x00   # Reserved
    )
    
    # PTP timestamp (8 bytes)
    timestamp = struct.pack('!QQ', int(time.time() * 1000000000), 0)
    
    # Source port identity (10 bytes)
    source_port = struct.pack('!10s', b'TEST_PORT')
    
    # Clock identity (8 bytes)
    clock_id = struct.pack('!8s', b'TEST_CLK')
    
    return ptp_header + timestamp + source_port + clock_id

def send_ptp_traffic(interface='enp3s0', duration=30):
    """Отправка PTP трафика на указанный интерфейс"""
    print(f"Генерация PTP трафика на {interface} в течение {duration} секунд...")
    
    try:
        # Создаем UDP сокет
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # PTP порты
        ptp_ports = [319, 320]  # Event и General
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration:
            for port in ptp_ports:
                # Создаем PTP пакет
                ptp_packet = create_ptp_packet(sequence_id=packet_count + 1)
                
                # Отправляем пакет
                try:
                    sock.sendto(ptp_packet, ('255.255.255.255', port))
                    packet_count += 1
                    print(f"Отправлен PTP пакет #{packet_count} на порт {port}")
                except Exception as e:
                    print(f"Ошибка отправки пакета: {e}")
                
                time.sleep(0.1)  # 100ms между пакетами
        
        sock.close()
        print(f"Генерация завершена. Отправлено {packet_count} пакетов.")
        
    except Exception as e:
        print(f"Ошибка при генерации PTP трафика: {e}")

def monitor_ptp_traffic(interface='enp3s0', duration=30):
    """Мониторинг PTP трафика на указанном интерфейсе"""
    print(f"Мониторинг PTP трафика на {interface} в течение {duration} секунд...")
    
    try:
        # Запускаем tcpdump для мониторинга PTP трафика
        import subprocess
        
        cmd = [
            'sudo', 'tcpdump', 
            '-i', interface,
            '-n',  # Не резолвить имена
            'port 319 or port 320',  # PTP порты
            '-c', '100'  # Максимум 100 пакетов
        ]
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration:
            line = process.stdout.readline()
            if line:
                packet_count += 1
                print(f"PTP пакет #{packet_count}: {line.strip()}")
            else:
                time.sleep(0.1)
        
        process.terminate()
        print(f"Мониторинг завершен. Обнаружено {packet_count} PTP пакетов.")
        
    except Exception as e:
        print(f"Ошибка при мониторинге PTP трафика: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Генерация и мониторинг PTP трафика')
    parser.add_argument('--interface', default='enp3s0', help='Сетевой интерфейс')
    parser.add_argument('--duration', type=int, default=30, help='Длительность в секундах')
    parser.add_argument('--mode', choices=['send', 'monitor', 'both'], default='both', 
                       help='Режим работы')
    
    args = parser.parse_args()
    
    if args.mode in ['send', 'both']:
        # Запускаем генерацию в отдельном потоке
        sender_thread = threading.Thread(
            target=send_ptp_traffic, 
            args=(args.interface, args.duration)
        )
        sender_thread.start()
    
    if args.mode in ['monitor', 'both']:
        # Запускаем мониторинг
        monitor_ptp_traffic(args.interface, args.duration)
    
    if args.mode == 'both':
        sender_thread.join()
    
    print("Тест завершен.") 