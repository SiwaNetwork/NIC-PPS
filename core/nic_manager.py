"""
Intel NIC Manager - основной класс для работы с сетевыми картами Intel
"""

import os
import subprocess
import netifaces
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Импортируем PPSMode из timenic_manager чтобы избежать дублирования
try:
    from .timenic_manager import PPSMode
except ImportError:
    # Если не удается импортировать, определяем локально
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
            print(f"Установка PPS режима: {interface} -> {mode.value}")
            
            # Проверяем возможности PPS
            capabilities = self.check_pps_capabilities(interface)
            print(f"PPS возможности для {interface}: {capabilities}")
            
            if mode == PPSMode.DISABLED:
                # Отключаем PPS
                print(f"Отключение PPS для {interface}")
                return self._disable_pps(interface)
            elif mode == PPSMode.INPUT:
                # Включаем только входной PPS
                print(f"Включение PPS input для {interface}")
                return self._enable_pps_input(interface)
            elif mode == PPSMode.OUTPUT:
                # Включаем только выходной PPS
                print(f"Включение PPS output для {interface}")
                return self._enable_pps_output(interface)
            elif mode == PPSMode.BOTH:
                # Включаем оба режима
                print(f"Включение PPS both для {interface}")
                return self._enable_pps_both(interface)
            else:
                print(f"Неизвестный режим PPS: {mode}")
                return False
            
        except Exception as e:
            print(f"Ошибка при установке PPS режима: {e}")
            return False
    
    def _disable_pps(self, interface: str) -> bool:
        """Отключение PPS"""
        try:
            success = True
            
            # Метод 1: Через sysfs
            pps_input_path = f"/sys/class/net/{interface}/pps_input"
            pps_output_path = f"/sys/class/net/{interface}/pps_output"
            
            if os.path.exists(pps_input_path):
                try:
                    with open(pps_input_path, 'w') as f:
                        f.write("0")
                    print(f"✓ PPS input отключен через sysfs для {interface}")
                except Exception as e:
                    print(f"✗ Ошибка отключения PPS input: {e}")
                    success = False
            
            if os.path.exists(pps_output_path):
                try:
                    with open(pps_output_path, 'w') as f:
                        f.write("0")
                    print(f"✓ PPS output отключен через sysfs для {interface}")
                except Exception as e:
                    print(f"✗ Ошибка отключения PPS output: {e}")
                    success = False
            
            # Метод 2: Через testptp
            ptp_device = self._get_ptp_device_for_interface(interface)
            if ptp_device:
                try:
                    # Отключаем PPS через testptp с sudo
                    # Отключаем периодический выход
                    result1 = subprocess.run(["sudo", "testptp", "-d", ptp_device, "-p", "0"], 
                                          capture_output=True, text=True, timeout=10)
                    # Отключаем внешние временные метки
                    result2 = subprocess.run(["sudo", "testptp", "-d", ptp_device, "-e", "0"], 
                                          capture_output=True, text=True, timeout=10)
                    
                    if result1.returncode == 0 and result2.returncode == 0:
                        print(f"✓ PPS отключен через testptp для {interface} ({ptp_device})")
                        success = True
                    else:
                        print(f"✗ testptp ошибка отключения: {result1.stderr} {result2.stderr}")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                    print(f"✗ testptp исключение при отключении: {e}")
            
            # Метод 3: Через phc_ctl
            try:
                result1 = subprocess.run(["sudo", "phc_ctl", "-d", ptp_device, "-e", "0"], 
                                      capture_output=True, text=True, timeout=10)
                result2 = subprocess.run(["sudo", "phc_ctl", "-d", ptp_device, "-i", "0"], 
                                      capture_output=True, text=True, timeout=10)
                
                if result1.returncode == 0 and result2.returncode == 0:
                    print(f"✓ PPS отключен через phc_ctl для {interface}")
                    success = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                pass
                
            return success
            
        except Exception as e:
            print(f"Ошибка при отключении PPS: {e}")
            return False
    
    def _enable_pps_input(self, interface: str) -> bool:
        """Включение входного PPS"""
        try:
            # Метод 1: Через sysfs
            pps_input_path = f"/sys/class/net/{interface}/pps_input"
            if os.path.exists(pps_input_path):
                try:
                    with open(pps_input_path, 'w') as f:
                        f.write("1")
                    print(f"✓ PPS input включен через sysfs для {interface}")
                    return True
                except Exception as e:
                    print(f"✗ Ошибка sysfs PPS input: {e}")
            
            # Метод 2: Через testptp (основной метод)
            ptp_device = self._get_ptp_device_for_interface(interface)
            if ptp_device:
                try:
                    # Включаем PPS вход через testptp с sudo
                    # Используем параметр -L для настройки пина как внешней временной метки
                    result = subprocess.run(["sudo", "testptp", "-d", ptp_device, "-L", "0,1"], 
                                         capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(f"✓ PPS input включен через testptp для {interface} ({ptp_device})")
                        return True
                    else:
                        print(f"✗ testptp ошибка: {result.stderr}")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                    print(f"✗ testptp исключение: {e}")
            
            # Метод 3: Через phc_ctl (альтернативный метод)
            try:
                result = subprocess.run(["sudo", "phc_ctl", "-d", ptp_device, "-i", "1"], 
                                     capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✓ PPS input включен через phc_ctl для {interface}")
                    return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                pass
                
        except Exception as e:
            print(f"Ошибка при включении PPS input: {e}")
        return False
    
    def _enable_pps_output(self, interface: str) -> bool:
        """Включение выходного PPS"""
        try:
            # Метод 1: Через sysfs
            pps_output_path = f"/sys/class/net/{interface}/pps_output"
            if os.path.exists(pps_output_path):
                try:
                    with open(pps_output_path, 'w') as f:
                        f.write("1")
                    print(f"✓ PPS output включен через sysfs для {interface}")
                    return True
                except Exception as e:
                    print(f"✗ Ошибка sysfs PPS output: {e}")
            
            # Метод 2: Через testptp (основной метод)
            ptp_device = self._get_ptp_device_for_interface(interface)
            if ptp_device:
                try:
                    # Включаем PPS выход через testptp с sudo
                    # Используем параметр -p для периодического выхода (PPS)
                    result = subprocess.run(["sudo", "testptp", "-d", ptp_device, "-p", "1000000000"], 
                                         capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(f"✓ PPS output включен через testptp для {interface} ({ptp_device})")
                        return True
                    else:
                        print(f"✗ testptp ошибка: {result.stderr}")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                    print(f"✗ testptp исключение: {e}")
            
            # Метод 3: Через phc_ctl (альтернативный метод)
            try:
                result = subprocess.run(["sudo", "phc_ctl", "-d", ptp_device, "-e", "1"], 
                                     capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✓ PPS output включен через phc_ctl для {interface}")
                    return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                pass
                
        except Exception as e:
            print(f"Ошибка при включении PPS output: {e}")
        return False
    
    def _get_ptp_device_for_interface(self, interface: str) -> Optional[str]:
        """Получение PTP устройства для интерфейса"""
        try:
            # Получаем номер PTP устройства через ethtool
            result = subprocess.run(["ethtool", "-T", interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if "PTP Hardware Clock:" in line:
                        clock_num = line.split(':')[1].strip()
                        ptp_device = f"/dev/ptp{clock_num}"
                        if os.path.exists(ptp_device):
                            return ptp_device
        except Exception:
            pass
        
        # Резервный метод: ищем все PTP устройства
        ptp_devices = self._find_ptp_devices(interface)
        if ptp_devices:
            return ptp_devices[0]
        
        return None
    
    def _find_ptp_devices(self, interface: str) -> List[str]:
        """Поиск PTP устройств для интерфейса"""
        ptp_devices = []
        try:
            # Ищем PTP устройства в /dev
            import glob
            for ptp_device in glob.glob("/dev/ptp*"):
                ptp_devices.append(ptp_device)
            
            # Также проверяем /sys/class/ptp
            if os.path.exists("/sys/class/ptp"):
                for ptp_dir in os.listdir("/sys/class/ptp"):
                    ptp_path = f"/dev/ptp{ptp_dir}"
                    if os.path.exists(ptp_path):
                        ptp_devices.append(ptp_path)
                        
        except Exception:
            pass
        
        return ptp_devices
    
    def check_pps_capabilities(self, interface: str) -> Dict[str, bool]:
        """Проверка возможностей PPS управления для интерфейса"""
        capabilities = {
            'sysfs_input': False,
            'sysfs_output': False,
            'ethtool': False,
            'testptp': False,
            'ptp_devices': []
        }
        
        try:
            # Проверяем sysfs
            pps_input_path = f"/sys/class/net/{interface}/pps_input"
            pps_output_path = f"/sys/class/net/{interface}/pps_output"
            
            if os.path.exists(pps_input_path):
                capabilities['sysfs_input'] = True
            
            if os.path.exists(pps_output_path):
                capabilities['sysfs_output'] = True
            
            # Проверяем ethtool
            try:
                result = subprocess.run(["ethtool", "-T", interface], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and "PPS" in result.stdout:
                    capabilities['ethtool'] = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Проверяем testptp
            try:
                result = subprocess.run(["testptp", "--help"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    capabilities['testptp'] = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Проверяем PTP устройства
            ptp_devices = self._find_ptp_devices(interface)
            capabilities['ptp_devices'] = ptp_devices
            
        except Exception as e:
            print(f"Ошибка при проверке PPS возможностей: {e}")
        
        return capabilities
    
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
            
            # Добавляем PTP статистику
            ptp_stats = self.get_ptp_statistics(interface)
            stats.update(ptp_stats)
            
            return stats
        except Exception as e:
            print(f"Ошибка при получении статистики: {e}")
            return {}
    
    def get_ptp_statistics(self, interface: str) -> Dict:
        """Получение PTP статистики"""
        ptp_stats = {
            'ptp_rx_packets': 0,
            'ptp_tx_packets': 0,
            'ptp_rx_bytes': 0,
            'ptp_tx_bytes': 0,
            'ptp_sync_packets': 0,
            'ptp_delay_req_packets': 0,
            'ptp_follow_up_packets': 0,
            'ptp_delay_resp_packets': 0
        }
        
        try:
            # Пытаемся получить PTP статистику через ethtool
            result = subprocess.run(
                ["ethtool", "--statistics", interface], 
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout
                lines = output.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if 'ptp' in line.lower() or 'sync' in line.lower():
                        # Парсим PTP статистику
                        if 'rx' in line.lower() and 'packet' in line.lower():
                            try:
                                value = int(line.split()[-1])
                                if 'ptp' in line.lower():
                                    ptp_stats['ptp_rx_packets'] = value
                                elif 'sync' in line.lower():
                                    ptp_stats['ptp_sync_packets'] = value
                            except (ValueError, IndexError):
                                pass
                        elif 'tx' in line.lower() and 'packet' in line.lower():
                            try:
                                value = int(line.split()[-1])
                                if 'ptp' in line.lower():
                                    ptp_stats['ptp_tx_packets'] = value
                            except (ValueError, IndexError):
                                pass
            
            # Пытаемся получить PTP статистику через /proc/net/dev
            try:
                with open('/proc/net/dev', 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if interface in line:
                            parts = line.split()
                            if len(parts) >= 17:
                                # Формат: interface rx_bytes rx_packets rx_errors rx_dropped tx_bytes tx_packets tx_errors tx_dropped
                                ptp_stats['ptp_rx_bytes'] = int(parts[1])  # Общие RX байты
                                ptp_stats['ptp_tx_bytes'] = int(parts[9])  # Общие TX байты
                                ptp_stats['ptp_rx_packets'] = int(parts[2])  # Общие RX пакеты
                                ptp_stats['ptp_tx_packets'] = int(parts[10])  # Общие TX пакеты
                            break
            except Exception:
                pass
                
        except Exception as e:
            print(f"Ошибка при получении PTP статистики: {e}")
        
        return ptp_stats