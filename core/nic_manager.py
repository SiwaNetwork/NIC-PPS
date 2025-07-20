"""
Intel NIC Manager - основной класс для работы с сетевыми картами Intel
"""

import os
import subprocess
import psutil
import netifaces
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class PPSMode(Enum):
    """Режимы работы PPS"""
    DISABLED = "disabled"
    INPUT = "input"
    OUTPUT = "output"
    BOTH = "both"


@dataclass
class NICInfo:
    """Информация о сетевой карте"""
    name: str
    mac_address: str
    ip_address: str
    status: str
    speed: str
    duplex: str
    pps_mode: PPSMode
    tcxo_enabled: bool
    temperature: Optional[float] = None


class IntelNICManager:
    """Менеджер для работы с сетевыми картами Intel"""
    
    def __init__(self):
        self.nic_list = []
        self._discover_nics()
    
    def _discover_nics(self):
        """Обнаружение сетевых карт Intel"""
        try:
            # Получаем список всех сетевых интерфейсов
            interfaces = netifaces.interfaces()
            
            for interface in interfaces:
                if self._is_intel_nic(interface):
                    nic_info = self._get_nic_info(interface)
                    if nic_info:
                        self.nic_list.append(nic_info)
        except Exception as e:
            print(f"Ошибка при обнаружении NIC: {e}")
    
    def _is_intel_nic(self, interface: str) -> bool:
        """Проверка, является ли интерфейс картой Intel"""
        try:
            # Проверяем драйвер и производителя
            driver_path = f"/sys/class/net/{interface}/device/driver"
            if os.path.exists(driver_path):
                driver = os.path.basename(os.readlink(driver_path))
                return "igb" in driver or "i40e" in driver or "ixgbe" in driver
        except:
            pass
        return False
    
    def _get_nic_info(self, interface: str) -> Optional[NICInfo]:
        """Получение информации о сетевой карте"""
        try:
            # Получаем MAC адрес
            mac = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
            
            # Получаем IP адрес
            ip = ""
            if netifaces.AF_INET in netifaces.ifaddresses(interface):
                ip = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
            
            # Получаем статус
            status = "up" if os.path.exists(f"/sys/class/net/{interface}/carrier") else "down"
            
            # Получаем скорость и дуплекс
            speed = self._get_interface_speed(interface)
            duplex = self._get_interface_duplex(interface)
            
            # Проверяем PPS режим
            pps_mode = self._get_pps_mode(interface)
            
            # Проверяем TCXO
            tcxo_enabled = self._is_tcxo_enabled(interface)
            
            return NICInfo(
                name=interface,
                mac_address=mac,
                ip_address=ip,
                status=status,
                speed=speed,
                duplex=duplex,
                pps_mode=pps_mode,
                tcxo_enabled=tcxo_enabled
            )
        except Exception as e:
            print(f"Ошибка при получении информации о {interface}: {e}")
            return None
    
    def _get_interface_speed(self, interface: str) -> str:
        """Получение скорости интерфейса"""
        try:
            with open(f"/sys/class/net/{interface}/speed", 'r') as f:
                speed = f.read().strip()
                return f"{speed} Mbps"
        except:
            return "Unknown"
    
    def _get_interface_duplex(self, interface: str) -> str:
        """Получение режима дуплекса"""
        try:
            with open(f"/sys/class/net/{interface}/duplex", 'r') as f:
                return f.read().strip()
        except:
            return "Unknown"
    
    def _get_pps_mode(self, interface: str) -> PPSMode:
        """Получение режима PPS"""
        try:
            # Проверяем наличие PPS файлов
            pps_input = os.path.exists(f"/sys/class/net/{interface}/pps_input")
            pps_output = os.path.exists(f"/sys/class/net/{interface}/pps_output")
            
            if pps_input and pps_output:
                return PPSMode.BOTH
            elif pps_input:
                return PPSMode.INPUT
            elif pps_output:
                return PPSMode.OUTPUT
            else:
                return PPSMode.DISABLED
        except:
            return PPSMode.DISABLED
    
    def _is_tcxo_enabled(self, interface: str) -> bool:
        """Проверка включен ли TCXO"""
        try:
            # Проверяем наличие TCXO файлов
            tcxo_path = f"/sys/class/net/{interface}/device/tcxo_enabled"
            if os.path.exists(tcxo_path):
                with open(tcxo_path, 'r') as f:
                    return f.read().strip() == "1"
        except:
            pass
        return False
    
    def get_all_nics(self) -> List[NICInfo]:
        """Получение списка всех NIC карт"""
        return self.nic_list
    
    def get_nic_by_name(self, name: str) -> Optional[NICInfo]:
        """Получение NIC по имени"""
        for nic in self.nic_list:
            if nic.name == name:
                return nic
        return None
    
    def set_pps_mode(self, interface: str, mode: PPSMode) -> bool:
        """Установка режима PPS"""
        try:
            if mode == PPSMode.DISABLED:
                # Отключаем PPS
                self._disable_pps(interface)
            elif mode == PPSMode.INPUT:
                # Включаем только входной PPS
                self._enable_pps_input(interface)
            elif mode == PPSMode.OUTPUT:
                # Включаем только выходной PPS
                self._enable_pps_output(interface)
            elif mode == PPSMode.BOTH:
                # Включаем оба режима
                self._enable_pps_both(interface)
            
            # Обновляем информацию о карте
            self._discover_nics()
            return True
        except Exception as e:
            print(f"Ошибка при установке PPS режима: {e}")
            return False
    
    def _disable_pps(self, interface: str):
        """Отключение PPS"""
        try:
            # Отключаем PPS через sysfs или ethtool
            subprocess.run(["ethtool", "-T", interface, "--pps-disable"], check=True)
        except subprocess.CalledProcessError:
            # Если ethtool не поддерживает, пробуем через sysfs
            pps_input = f"/sys/class/net/{interface}/pps_input"
            pps_output = f"/sys/class/net/{interface}/pps_output"
            
            if os.path.exists(pps_input):
                with open(pps_input, 'w') as f:
                    f.write("0")
            if os.path.exists(pps_output):
                with open(pps_output, 'w') as f:
                    f.write("0")
    
    def _enable_pps_input(self, interface: str):
        """Включение входного PPS"""
        try:
            subprocess.run(["ethtool", "-T", interface, "--pps-input"], check=True)
        except subprocess.CalledProcessError:
            pps_input = f"/sys/class/net/{interface}/pps_input"
            if os.path.exists(pps_input):
                with open(pps_input, 'w') as f:
                    f.write("1")
    
    def _enable_pps_output(self, interface: str):
        """Включение выходного PPS"""
        try:
            subprocess.run(["ethtool", "-T", interface, "--pps-output"], check=True)
        except subprocess.CalledProcessError:
            pps_output = f"/sys/class/net/{interface}/pps_output"
            if os.path.exists(pps_output):
                with open(pps_output, 'w') as f:
                    f.write("1")
    
    def _enable_pps_both(self, interface: str):
        """Включение обоих режимов PPS"""
        self._enable_pps_input(interface)
        self._enable_pps_output(interface)
    
    def set_tcxo_enabled(self, interface: str, enabled: bool) -> bool:
        """Включение/отключение TCXO"""
        try:
            tcxo_path = f"/sys/class/net/{interface}/device/tcxo_enabled"
            if os.path.exists(tcxo_path):
                with open(tcxo_path, 'w') as f:
                    f.write("1" if enabled else "0")
                
                # Обновляем информацию о карте
                self._discover_nics()
                return True
        except Exception as e:
            print(f"Ошибка при настройке TCXO: {e}")
        return False
    
    def get_temperature(self, interface: str) -> Optional[float]:
        """Получение температуры карты"""
        try:
            temp_path = f"/sys/class/net/{interface}/device/temp1_input"
            if os.path.exists(temp_path):
                with open(temp_path, 'r') as f:
                    temp_raw = int(f.read().strip())
                    return temp_raw / 1000.0  # Температура в миллиградусах
        except:
            pass
        return None
    
    def get_statistics(self, interface: str) -> Dict:
        """Получение статистики карты"""
        try:
            stats = {}
            
            # Статистика через /proc/net/dev
            with open("/proc/net/dev", 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if interface in line:
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
            
            return stats
        except Exception as e:
            print(f"Ошибка при получении статистики: {e}")
            return {}