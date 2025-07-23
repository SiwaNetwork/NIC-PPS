"""
Драйвер для работы с Intel NIC картами
"""

import os
import subprocess
import time
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod


class IntelDriver(ABC):
    """Базовый класс драйвера для Intel NIC карт"""
    
    def __init__(self, interface: str):
        self.interface = interface
        self.sysfs_path = f"/sys/class/net/{interface}"
        self.device_path = f"{self.sysfs_path}/device"
    
    @abstractmethod
    def get_driver_name(self) -> str:
        """Получение имени драйвера"""
        pass
    
    @abstractmethod
    def get_device_id(self) -> str:
        """Получение ID устройства"""
        pass
    
    def get_device_info(self) -> Dict:
        """Получение информации об устройстве"""
        info = {
            'interface': self.interface,
            'driver': self.get_driver_name(),
            'device_id': self.get_device_id(),
            'sysfs_path': self.sysfs_path,
            'device_path': self.device_path
        }
        
        # Добавляем дополнительную информацию
        if os.path.exists(f"{self.device_path}/vendor"):
            with open(f"{self.device_path}/vendor", 'r') as f:
                info['vendor'] = f.read().strip()
        
        if os.path.exists(f"{self.device_path}/device"):
            with open(f"{self.device_path}/device", 'r') as f:
                info['device'] = f.read().strip()
        
        return info
    
    def get_interface_status(self) -> str:
        """Получение статуса интерфейса"""
        carrier_path = f"{self.sysfs_path}/carrier"
        if os.path.exists(carrier_path):
            with open(carrier_path, 'r') as f:
                return "up" if f.read().strip() == "1" else "down"
        return "unknown"
    
    def get_interface_speed(self) -> str:
        """Получение скорости интерфейса"""
        speed_path = f"{self.sysfs_path}/speed"
        if os.path.exists(speed_path):
            with open(speed_path, 'r') as f:
                speed = f.read().strip()
                return f"{speed} Mbps"
        return "Unknown"
    
    def get_interface_duplex(self) -> str:
        """Получение режима дуплекса"""
        duplex_path = f"{self.sysfs_path}/duplex"
        if os.path.exists(duplex_path):
            with open(duplex_path, 'r') as f:
                return f.read().strip()
        return "Unknown"
    
    def get_temperature(self) -> Optional[float]:
        """Получение температуры устройства"""
        temp_path = f"{self.device_path}/temp1_input"
        if os.path.exists(temp_path):
            with open(temp_path, 'r') as f:
                temp_raw = int(f.read().strip())
                return temp_raw / 1000.0  # Температура в миллиградусах
        return None
    
    def get_statistics(self) -> Dict:
        """Получение статистики интерфейса"""
        stats = {}
        try:
            with open("/proc/net/dev", 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if self.interface in line:
                        parts = line.split()
                        if len(parts) >= 17:
                            stats = {
                                'rx_bytes': int(parts[1]),
                                'rx_packets': int(parts[2]),
                                'rx_errors': int(parts[3]),
                                'rx_dropped': int(parts[4]),
                                'tx_bytes': int(parts[9]),
                                'tx_packets': int(parts[10]),
                                'tx_errors': int(parts[11]),
                                'tx_dropped': int(parts[12])
                            }
                            break
        except Exception as e:
            print(f"Ошибка при получении статистики: {e}")
        
        return stats


class IGBDriver(IntelDriver):
    """Драйвер для Intel IGB (Gigabit Ethernet)"""
    
    def get_driver_name(self) -> str:
        return "igb"
    
    def get_device_id(self) -> str:
        return "IGB"
    
    def get_pps_mode(self) -> str:
        """Получение режима PPS для IGB"""
        # IGB поддерживает PPS через ethtool
        try:
            result = subprocess.run(
                ["ethtool", "-T", self.interface],
                capture_output=True, text=True, check=True
            )
            if "PPS" in result.stdout:
                if "PPS input" in result.stdout and "PPS output" in result.stdout:
                    return "both"
                elif "PPS input" in result.stdout:
                    return "input"
                elif "PPS output" in result.stdout:
                    return "output"
                else:
                    return "disabled"
        except subprocess.CalledProcessError:
            pass
        return "disabled"
    
    def set_pps_mode(self, mode: str) -> bool:
        """Установка режима PPS для IGB"""
        # ethtool не поддерживает управление PPS напрямую
        # Нужно использовать testptp с PTP устройством
        print(f"Установка PPS режима через ethtool не поддерживается")
        return False
    
    def get_tcxo_status(self) -> bool:
        """Получение статуса TCXO для IGB"""
        # IGB может не поддерживать TCXO
        return False
    
    def set_tcxo_enabled(self, enabled: bool) -> bool:
        """Установка TCXO для IGB"""
        # IGB не поддерживает TCXO
        return False


class I40EDriver(IntelDriver):
    """Драйвер для Intel I40E (40 Gigabit Ethernet)"""
    
    def get_driver_name(self) -> str:
        return "i40e"
    
    def get_device_id(self) -> str:
        return "I40E"
    
    def get_pps_mode(self) -> str:
        """Получение режима PPS для I40E"""
        # Проверяем через sysfs
        pps_input = os.path.exists(f"{self.sysfs_path}/pps_input")
        pps_output = os.path.exists(f"{self.sysfs_path}/pps_output")
        
        if pps_input and pps_output:
            return "both"
        elif pps_input:
            return "input"
        elif pps_output:
            return "output"
        else:
            return "disabled"
    
    def set_pps_mode(self, mode: str) -> bool:
        """Установка режима PPS для I40E"""
        try:
            if mode == "disabled":
                # Отключаем PPS
                pps_input = f"{self.sysfs_path}/pps_input"
                pps_output = f"{self.sysfs_path}/pps_output"
                
                if os.path.exists(pps_input):
                    with open(pps_input, 'w') as f:
                        f.write("0")
                if os.path.exists(pps_output):
                    with open(pps_output, 'w') as f:
                        f.write("0")
            elif mode == "input":
                pps_input = f"{self.sysfs_path}/pps_input"
                if os.path.exists(pps_input):
                    with open(pps_input, 'w') as f:
                        f.write("1")
            elif mode == "output":
                pps_output = f"{self.sysfs_path}/pps_output"
                if os.path.exists(pps_output):
                    with open(pps_output, 'w') as f:
                        f.write("1")
            elif mode == "both":
                pps_input = f"{self.sysfs_path}/pps_input"
                pps_output = f"{self.sysfs_path}/pps_output"
                
                if os.path.exists(pps_input):
                    with open(pps_input, 'w') as f:
                        f.write("1")
                if os.path.exists(pps_output):
                    with open(pps_output, 'w') as f:
                        f.write("1")
            
            return True
        except Exception as e:
            print(f"Ошибка установки PPS для I40E: {e}")
            return False
    
    def get_tcxo_status(self) -> bool:
        """Получение статуса TCXO для I40E"""
        tcxo_path = f"{self.device_path}/tcxo_enabled"
        if os.path.exists(tcxo_path):
            with open(tcxo_path, 'r') as f:
                return f.read().strip() == "1"
        return False
    
    def set_tcxo_enabled(self, enabled: bool) -> bool:
        """Установка TCXO для I40E"""
        try:
            tcxo_path = f"{self.device_path}/tcxo_enabled"
            if os.path.exists(tcxo_path):
                with open(tcxo_path, 'w') as f:
                    f.write("1" if enabled else "0")
                return True
        except Exception as e:
            print(f"Ошибка установки TCXO для I40E: {e}")
        return False


class IXGBEDriver(IntelDriver):
    """Драйвер для Intel IXGBE (10 Gigabit Ethernet)"""
    
    def get_driver_name(self) -> str:
        return "ixgbe"
    
    def get_device_id(self) -> str:
        return "IXGBE"
    
    def get_pps_mode(self) -> str:
        """Получение режима PPS для IXGBE"""
        # IXGBE поддерживает PPS через ethtool
        try:
            result = subprocess.run(
                ["ethtool", "-T", self.interface],
                capture_output=True, text=True, check=True
            )
            if "PPS" in result.stdout:
                if "PPS input" in result.stdout and "PPS output" in result.stdout:
                    return "both"
                elif "PPS input" in result.stdout:
                    return "input"
                elif "PPS output" in result.stdout:
                    return "output"
                else:
                    return "disabled"
        except subprocess.CalledProcessError:
            pass
        return "disabled"
    
    def set_pps_mode(self, mode: str) -> bool:
        """Установка режима PPS для IXGBE"""
        # ethtool не поддерживает управление PPS напрямую
        # Нужно использовать testptp с PTP устройством
        print(f"Установка PPS режима через ethtool не поддерживается")
        return False
    
    def get_tcxo_status(self) -> bool:
        """Получение статуса TCXO для IXGBE"""
        # IXGBE может поддерживать TCXO через sysfs
        tcxo_path = f"{self.device_path}/tcxo_enabled"
        if os.path.exists(tcxo_path):
            with open(tcxo_path, 'r') as f:
                return f.read().strip() == "1"
        return False
    
    def set_tcxo_enabled(self, enabled: bool) -> bool:
        """Установка TCXO для IXGBE"""
        try:
            tcxo_path = f"{self.device_path}/tcxo_enabled"
            if os.path.exists(tcxo_path):
                with open(tcxo_path, 'w') as f:
                    f.write("1" if enabled else "0")
                return True
        except Exception as e:
            print(f"Ошибка установки TCXO для IXGBE: {e}")
        return False


def create_driver(interface: str) -> Optional[IntelDriver]:
    """Создание драйвера для указанного интерфейса"""
    try:
        # Определяем тип драйвера
        driver_path = f"/sys/class/net/{interface}/device/driver"
        if os.path.exists(driver_path):
            driver_name = os.path.basename(os.readlink(driver_path))
            
            if "igb" in driver_name:
                return IGBDriver(interface)
            elif "i40e" in driver_name:
                return I40EDriver(interface)
            elif "ixgbe" in driver_name:
                return IXGBEDriver(interface)
            else:
                print(f"Неподдерживаемый драйвер: {driver_name}")
                return None
        else:
            print(f"Драйвер не найден для интерфейса {interface}")
            return None
    except Exception as e:
        print(f"Ошибка создания драйвера для {interface}: {e}")
        return None


def get_supported_drivers() -> List[str]:
    """Получение списка поддерживаемых драйверов"""
    return ["igb", "i40e", "ixgbe"]


def detect_intel_nics() -> List[str]:
    """Обнаружение Intel NIC карт"""
    intel_nics = []
    
    try:
        # Получаем список всех сетевых интерфейсов
        interfaces = os.listdir("/sys/class/net")
        
        for interface in interfaces:
            driver_path = f"/sys/class/net/{interface}/device/driver"
            if os.path.exists(driver_path):
                driver_name = os.path.basename(os.readlink(driver_path))
                
                # Проверяем, является ли это Intel драйвером
                if any(intel_driver in driver_name for intel_driver in get_supported_drivers()):
                    intel_nics.append(interface)
    
    except Exception as e:
        print(f"Ошибка при обнаружении Intel NIC карт: {e}")
    
    return intel_nics