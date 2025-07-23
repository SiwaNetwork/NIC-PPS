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
                # Поддерживаемые драйверы Intel
                intel_drivers = ["igb", "igc", "i40e", "ixgbe", "e1000e", "e1000"]
                return any(d in driver.lower() for d in intel_drivers)
        except Exception:
            pass
        
        # Дополнительная проверка через ethtool если команда доступна
        try:
            result = subprocess.run(["ethtool", "-i", interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                output_lower = result.stdout.lower()
                return "intel" in output_lower or any(d in output_lower for d in ["igb", "igc", "i40e", "ixgbe", "e1000"])
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return False
    
    def _get_nic_info(self, interface: str) -> Optional[NICInfo]:
        """Получение информации о сетевой карте"""
        try:
            # Получаем MAC адрес
            mac = ""
            try:
                mac_info = netifaces.ifaddresses(interface).get(netifaces.AF_LINK, [])
                if mac_info:
                    mac = mac_info[0].get('addr', '')
            except Exception:
                pass
            
            # Получаем IP адрес
            ip = ""
            try:
                ip_info = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
                if ip_info:
                    ip = ip_info[0].get('addr', '')
            except Exception:
                pass
            
            # Получаем статус
            status = self._get_interface_status(interface)
            
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
    
    def _get_interface_status(self, interface: str) -> str:
        """Получение статуса интерфейса"""
        try:
            operstate_path = f"/sys/class/net/{interface}/operstate"
            if os.path.exists(operstate_path):
                with open(operstate_path, 'r') as f:
                    state = f.read().strip()
                    return "up" if state == "up" else "down"
        except Exception:
            pass
        return "unknown"
    
    def _get_interface_speed(self, interface: str) -> str:
        """Получение скорости интерфейса"""
        try:
            speed_path = f"/sys/class/net/{interface}/speed"
            if os.path.exists(speed_path):
                with open(speed_path, 'r') as f:
                    speed = f.read().strip()
                    if speed and speed != "-1":
                        return f"{speed} Mbps"
        except Exception:
            pass
        
        # Пробуем через ethtool
        try:
            result = subprocess.run(["ethtool", interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Speed:' in line:
                        return line.split(':')[1].strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return "Unknown"
    
    def _get_interface_duplex(self, interface: str) -> str:
        """Получение режима дуплекса"""
        try:
            duplex_path = f"/sys/class/net/{interface}/duplex"
            if os.path.exists(duplex_path):
                with open(duplex_path, 'r') as f:
                    return f.read().strip()
        except Exception:
            pass
        
        # Пробуем через ethtool
        try:
            result = subprocess.run(["ethtool", interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Duplex:' in line:
                        return line.split(':')[1].strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return "Unknown"
    
    def _get_pps_mode(self, interface: str) -> PPSMode:
        """Получение режима PPS"""
        try:
            # Проверяем наличие PPS файлов в sysfs
            pps_input_path = f"/sys/class/net/{interface}/pps_input"
            pps_output_path = f"/sys/class/net/{interface}/pps_output"
            
            pps_input = False
            pps_output = False
            
            if os.path.exists(pps_input_path):
                try:
                    with open(pps_input_path, 'r') as f:
                        pps_input = f.read().strip() == "1"
                except Exception:
                    pass
            
            if os.path.exists(pps_output_path):
                try:
                    with open(pps_output_path, 'r') as f:
                        pps_output = f.read().strip() == "1"
                except Exception:
                    pass
            
            if pps_input and pps_output:
                return PPSMode.BOTH
            elif pps_input:
                return PPSMode.INPUT
            elif pps_output:
                return PPSMode.OUTPUT
            
        except Exception:
            pass
        
        return PPSMode.DISABLED
    
    def _is_tcxo_enabled(self, interface: str) -> bool:
        """Проверка включен ли TCXO"""
        try:
            # Проверяем наличие TCXO файлов
            tcxo_paths = [
                f"/sys/class/net/{interface}/device/tcxo_enabled",
                f"/sys/class/net/{interface}/tcxo_enabled"
            ]
            
            for tcxo_path in tcxo_paths:
                if os.path.exists(tcxo_path):
                    try:
                        with open(tcxo_path, 'r') as f:
                            return f.read().strip() == "1"
                    except Exception:
                        continue
        except Exception:
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
                return self._disable_pps(interface)
            elif mode == PPSMode.INPUT:
                # Включаем только входной PPS
                return self._enable_pps_input(interface)
            elif mode == PPSMode.OUTPUT:
                # Включаем только выходной PPS
                return self._enable_pps_output(interface)
            elif mode == PPSMode.BOTH:
                # Включаем оба режима
                return self._enable_pps_both(interface)
            
        except Exception as e:
            print(f"Ошибка при установке PPS режима: {e}")
            return False
        
        return False
    
    def _disable_pps(self, interface: str) -> bool:
        """Отключение PPS"""
        try:
            # Отключаем PPS через sysfs
            success = True
            
            pps_input_path = f"/sys/class/net/{interface}/pps_input"
            pps_output_path = f"/sys/class/net/{interface}/pps_output"
            
            if os.path.exists(pps_input_path):
                try:
                    with open(pps_input_path, 'w') as f:
                        f.write("0")
                except Exception:
                    success = False
            
            if os.path.exists(pps_output_path):
                try:
                    with open(pps_output_path, 'w') as f:
                        f.write("0")
                except Exception:
                    success = False
            
            # Пробуем через ethtool как резервный вариант
            try:
                subprocess.run(["ethtool", "-T", interface, "--pps-disable"], 
                             check=True, timeout=10)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                pass
                
            return success
            
        except Exception:
            return False
    
    def _enable_pps_input(self, interface: str) -> bool:
        """Включение входного PPS"""
        try:
            pps_input_path = f"/sys/class/net/{interface}/pps_input"
            if os.path.exists(pps_input_path):
                try:
                    with open(pps_input_path, 'w') as f:
                        f.write("1")
                    return True
                except Exception:
                    pass
            
            # Пробуем через ethtool
            try:
                subprocess.run(["ethtool", "-T", interface, "--pps-input"], 
                             check=True, timeout=10)
                return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                pass
                
        except Exception:
            pass
        return False
    
    def _enable_pps_output(self, interface: str) -> bool:
        """Включение выходного PPS"""
        try:
            pps_output_path = f"/sys/class/net/{interface}/pps_output"
            if os.path.exists(pps_output_path):
                try:
                    with open(pps_output_path, 'w') as f:
                        f.write("1")
                    return True
                except Exception:
                    pass
            
            # ethtool не поддерживает управление PPS напрямую
            # Используем testptp через PTP устройство
            return False
                
        except Exception:
            pass
        return False
    
    def _enable_pps_both(self, interface: str) -> bool:
        """Включение обоих режимов PPS"""
        input_success = self._enable_pps_input(interface)
        output_success = self._enable_pps_output(interface)
        return input_success and output_success
    
    def set_tcxo_enabled(self, interface: str, enabled: bool) -> bool:
        """Включение/отключение TCXO"""
        try:
            tcxo_paths = [
                f"/sys/class/net/{interface}/device/tcxo_enabled",
                f"/sys/class/net/{interface}/tcxo_enabled"
            ]
            
            for tcxo_path in tcxo_paths:
                if os.path.exists(tcxo_path):
                    try:
                        with open(tcxo_path, 'w') as f:
                            f.write("1" if enabled else "0")
                        return True
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"Ошибка при настройке TCXO: {e}")
        return False
    
    def get_temperature(self, interface: str) -> Optional[float]:
        """Получение температуры карты"""
        try:
            # Поиск файлов температуры
            temp_paths = [
                f"/sys/class/net/{interface}/device/temp1_input",
                f"/sys/class/net/{interface}/device/hwmon/hwmon*/temp1_input",
                f"/sys/class/net/{interface}/temperature"
            ]
            
            for temp_path in temp_paths:
                if '*' in temp_path:
                    # Для glob паттернов
                    import glob
                    for path in glob.glob(temp_path):
                        if os.path.exists(path):
                            try:
                                with open(path, 'r') as f:
                                    temp_raw = int(f.read().strip())
                                    return temp_raw / 1000.0  # Температура в миллиградусах
                            except Exception:
                                continue
                else:
                    if os.path.exists(temp_path):
                        try:
                            with open(temp_path, 'r') as f:
                                temp_raw = int(f.read().strip())
                                return temp_raw / 1000.0
                        except Exception:
                            continue
        except Exception:
            pass
        return None
    
    def get_statistics(self, interface: str) -> Dict:
        """Получение статистики карты"""
        try:
            stats = {}
            
            # Статистика через /sys/class/net/
            stats_paths = {
                'rx_bytes': f"/sys/class/net/{interface}/statistics/rx_bytes",
                'rx_packets': f"/sys/class/net/{interface}/statistics/rx_packets",
                'rx_errors': f"/sys/class/net/{interface}/statistics/rx_errors",
                'rx_dropped': f"/sys/class/net/{interface}/statistics/rx_dropped",
                'tx_bytes': f"/sys/class/net/{interface}/statistics/tx_bytes",
                'tx_packets': f"/sys/class/net/{interface}/statistics/tx_packets",
                'tx_errors': f"/sys/class/net/{interface}/statistics/tx_errors",
                'tx_dropped': f"/sys/class/net/{interface}/statistics/tx_dropped"
            }
            
            for stat_name, stat_path in stats_paths.items():
                if os.path.exists(stat_path):
                    try:
                        with open(stat_path, 'r') as f:
                            stats[stat_name] = int(f.read().strip())
                    except Exception:
                        stats[stat_name] = 0
                else:
                    stats[stat_name] = 0
            
            return stats
        except Exception as e:
            print(f"Ошибка при получении статистики: {e}")
            return {}