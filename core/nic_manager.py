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
            
            # Если sysfs не работает, пробуем через testptp
            if not pps_input and not pps_output:
                ptp_device = self._get_ptp_device_for_interface(interface)
                if ptp_device:
                    try:
                        # Проверяем текущую конфигурацию пинов через testptp
                        result = subprocess.run(["sudo", "-n", "testptp", "-d", ptp_device, "-l"], 
                                             capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            output = result.stdout
                            print(f"testptp -l результат для {interface}: {output}")
                            
                            # Анализируем вывод для определения режима
                            # func 2 = периодический выход (PPS output)
                            # func 1 = внешние временные метки (PPS input)
                            for line in output.split('\n'):
                                if 'func 2' in line:
                                    pps_output = True
                                elif 'func 1' in line:
                                    pps_input = True
                    except Exception as e:
                        print(f"Ошибка при проверке PPS через testptp: {e}")
            
            if pps_input and pps_output:
                return PPSMode.BOTH
            elif pps_input:
                return PPSMode.INPUT
            elif pps_output:
                return PPSMode.OUTPUT
            
        except Exception as e:
            print(f"Ошибка в _get_pps_mode: {e}")
        
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
    
    def refresh_nic_info(self, interface: str) -> Optional[NICInfo]:
        """Обновление информации о NIC"""
        try:
            # Получаем свежую информацию о NIC
            nic_info = self._get_nic_info(interface)
            if nic_info:
                # Обновляем информацию в списке
                for i, nic in enumerate(self.nic_list):
                    if nic.name == interface:
                        self.nic_list[i] = nic_info
                        return nic_info
        except Exception as e:
            print(f"Ошибка при обновлении информации о NIC {interface}: {e}")
        return None
    
    def set_pps_mode(self, interface: str, mode: PPSMode) -> bool:
        """Установка режима PPS"""
        try:
            print(f"Установка PPS режима: {interface} -> {mode.value}")
            
            # Проверяем возможности PPS
            capabilities = self.check_pps_capabilities(interface)
            print(f"PPS возможности для {interface}: {capabilities}")
            
            success = False
            if mode == PPSMode.DISABLED:
                # Отключаем PPS
                print(f"Отключение PPS для {interface}")
                success = self._disable_pps(interface)
            elif mode == PPSMode.INPUT:
                # Включаем только входной PPS
                print(f"Включение PPS input для {interface}")
                success = self._enable_pps_input(interface)
            elif mode == PPSMode.OUTPUT:
                # Включаем только выходной PPS
                print(f"Включение PPS output для {interface}")
                success = self._enable_pps_output(interface)
            elif mode == PPSMode.BOTH:
                # Включаем оба режима
                print(f"Включение PPS both для {interface}")
                success = self._enable_pps_both(interface)
            
            print(f"Результат установки PPS: {success}")
            
            # Обновляем информацию о карте
            if success:
                print(f"Обновление информации о NIC {interface} после изменения PPS")
                self.refresh_nic_info(interface)
            
            return success
            
        except Exception as e:
            print(f"Исключение при установке PPS режима: {e}")
            import traceback
            traceback.print_exc()
        return False
    
    def _disable_pps(self, interface: str) -> bool:
        """Отключение PPS для интерфейса"""
        print(f"Отключение PPS для {interface}")
        
        success = False
        
        # Метод 1: Через sysfs (если доступен)
        try:
            sysfs_paths = [
                f"/sys/class/net/{interface}/device/ptp/ptp*/pps_enable",
                f"/sys/class/net/{interface}/device/ptp*/pps_enable"
            ]
            
            for pattern in sysfs_paths:
                import glob
                for path in glob.glob(pattern):
                    try:
                        with open(path, 'w') as f:
                            f.write('0')
                        print(f"✓ PPS отключен через sysfs: {path}")
                        success = True
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Метод 2: Через testptp (основной метод)
        ptp_device = self._get_ptp_device_for_interface(interface)
        if ptp_device:
            try:
                print(f"Отключение PPS через testptp для {interface} ({ptp_device})")
                
                # Шаг 1: Отключаем периодический выход (устанавливаем период в 0)
                print(f"Отключение периодического выхода для {interface}")
                result1 = subprocess.run(["sudo", "-n", "testptp", "-d", ptp_device, "-p", "0"], 
                                      capture_output=True, text=True, timeout=10)
                print(f"Результат отключения периодического выхода: {result1.returncode}")
                
                # Шаг 2: Отключаем SDP0 (выходной пин) - устанавливаем func 0
                print(f"Отключение SDP0 (выходной пин) для {interface}")
                result2 = subprocess.run(["sudo", "-n", "testptp", "-d", ptp_device, "-L0,0"], 
                                      capture_output=True, text=True, timeout=10)
                print(f"Результат отключения SDP0: {result2.returncode}")
                
                # Шаг 3: Отключаем SDP1 (входной пин) - устанавливаем func 0
                print(f"Отключение SDP1 (входной пин) для {interface}")
                result3 = subprocess.run(["sudo", "-n", "testptp", "-d", ptp_device, "-L1,0"], 
                                      capture_output=True, text=True, timeout=10)
                print(f"Результат отключения SDP1: {result3.returncode}")
                
                # Шаг 4: Отключаем внешние временные метки
                print(f"Отключение внешних временных меток для {interface}")
                result4 = subprocess.run(["sudo", "-n", "testptp", "-d", ptp_device, "-e", "0"], 
                                      capture_output=True, text=True, timeout=10)
                print(f"Результат отключения внешних меток: {result4.returncode}")
                
                if result1.returncode == 0 and result2.returncode == 0 and result3.returncode == 0 and result4.returncode == 0:
                    print(f"✓ PPS полностью отключен через testptp для {interface}")
                    success = True
                else:
                    print(f"✗ Ошибки testptp при отключении:")
                    print(f"  Периодический выход: {result1.stderr}")
                    print(f"  SDP0: {result2.stderr}")
                    print(f"  SDP1: {result3.stderr}")
                    print(f"  Внешние метки: {result4.stderr}")
                    
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"✗ testptp исключение при отключении: {e}")
        
        # Метод 3: Через phc_ctl (резервный метод)
        if ptp_device:
                try:
                print(f"Пробуем отключить через phc_ctl для {interface}")
                result1 = subprocess.run(["sudo", "-n", "phc_ctl", "-d", ptp_device, "-e", "0"], 
                                      capture_output=True, text=True, timeout=10)
                result2 = subprocess.run(["sudo", "-n", "phc_ctl", "-d", ptp_device, "-p", "0"], 
                                      capture_output=True, text=True, timeout=10)
                
                if result1.returncode == 0 and result2.returncode == 0:
                    print(f"✓ PPS отключен через phc_ctl для {interface}")
                    success = True
                else:
                    print(f"✗ phc_ctl ошибки: {result1.stderr} {result2.stderr}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"✗ phc_ctl исключение: {e}")
            
        return success
    
    def _enable_pps_input(self, interface: str) -> bool:
        """Включение PPS input для интерфейса"""
        print(f"Включение PPS input для {interface}")
        
                    success = False
            
        # Метод 1: Через sysfs (если доступен)
        try:
            sysfs_paths = [
                f"/sys/class/net/{interface}/device/ptp/ptp*/pps_enable",
                f"/sys/class/net/{interface}/device/ptp*/pps_enable"
            ]
            
            for pattern in sysfs_paths:
                import glob
                for path in glob.glob(pattern):
                try:
                        with open(path, 'w') as f:
                            f.write('1')
                        print(f"✓ PPS input включен через sysfs: {path}")
                        success = True
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Метод 2: Через testptp (основной метод)
        ptp_device = self._get_ptp_device_for_interface(interface)
        if ptp_device:
            try:
                print(f"Включение PPS input через testptp для {interface} ({ptp_device})")
                
                # Шаг 1: Назначаем SDP1 как входной пин
                print(f"Настройка SDP1 как входной пин для {interface}")
                cmd1 = ["sudo", "-n", "testptp", "-d", ptp_device, "-L1,1"]
                print(f"Выполняем команду: {' '.join(cmd1)}")
                result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=10)
                print(f"Результат 1: returncode={result1.returncode}, stdout='{result1.stdout}', stderr='{result1.stderr}'")
                
                if result1.returncode == 0:
                    print(f"✓ PPS input включен через testptp для {interface} ({ptp_device})")
                    success = True
                else:
                    print(f"✗ testptp ошибка: {result1.stderr}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"✗ testptp исключение: {e}")
        
        # Метод 3: Через phc_ctl (альтернативный метод)
        if ptp_device:
            try:
                print("Пробуем phc_ctl...")
                result = subprocess.run(["sudo", "-n", "phc_ctl", "-d", ptp_device, "-i", "1"], 
                                     capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✓ PPS input включен через phc_ctl для {interface}")
                    success = True
                else:
                    print(f"✗ phc_ctl ошибка: {result.stderr}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"✗ phc_ctl исключение: {e}")
                
            return success
            
    def _enable_pps_output(self, interface: str) -> bool:
        """Включение PPS output для интерфейса"""
        print(f"Включение PPS output для {interface}")
        
        success = False
        
        # Метод 1: Через sysfs (если доступен)
        try:
            sysfs_paths = [
                f"/sys/class/net/{interface}/device/ptp/ptp*/pps_enable",
                f"/sys/class/net/{interface}/device/ptp*/pps_enable"
            ]
            
            for pattern in sysfs_paths:
                import glob
                for path in glob.glob(pattern):
                    try:
                        with open(path, 'w') as f:
                            f.write('1')
                        print(f"✓ PPS output включен через sysfs: {path}")
                        success = True
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Метод 2: Через testptp (основной метод)
        ptp_device = self._get_ptp_device_for_interface(interface)
        if ptp_device:
            try:
                print(f"Включение PPS output через testptp для {interface} ({ptp_device})")
                
                # Шаг 1: Назначаем SDP0 как выходной пин (периодический выход)
                print(f"Настройка SDP0 как выходной пин для {interface}")
                cmd1 = ["sudo", "-n", "testptp", "-d", ptp_device, "-L0,2"]
                print(f"Выполняем команду: {' '.join(cmd1)}")
                result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=10)
                print(f"Результат 1: returncode={result1.returncode}, stdout='{result1.stdout}', stderr='{result1.stderr}'")
                
                # Шаг 2: Устанавливаем период = 1 Гц (1 секунда)
                print(f"Установка периода 1 Гц для {interface}")
                cmd2 = ["sudo", "-n", "testptp", "-d", ptp_device, "-p", "1000000000"]
                print(f"Выполняем команду: {' '.join(cmd2)}")
                result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=10)
                print(f"Результат 2: returncode={result2.returncode}, stdout='{result2.stdout}', stderr='{result2.stderr}'")
                
                if result1.returncode == 0 and result2.returncode == 0:
                    print(f"✓ PPS output включен через testptp для {interface} ({ptp_device})")
                    success = True
                else:
                    print(f"✗ testptp ошибка: {result1.stderr} {result2.stderr}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"✗ testptp исключение: {e}")
        
        # Метод 3: Через phc_ctl (альтернативный метод)
        if ptp_device:
            try:
                print("Пробуем phc_ctl...")
                result = subprocess.run(["sudo", "-n", "phc_ctl", "-d", ptp_device, "-e", "1"], 
                                     capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✓ PPS output включен через phc_ctl для {interface}")
                    success = True
                else:
                    print(f"✗ phc_ctl ошибка: {result.stderr}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"✗ phc_ctl исключение: {e}")
                
        return success
    
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
            
            success = False
            for tcxo_path in tcxo_paths:
                if os.path.exists(tcxo_path):
                    try:
                        with open(tcxo_path, 'w') as f:
                            f.write("1" if enabled else "0")
                        success = True
                        break
                    except Exception:
                        continue
            
            # Если успешно изменили TCXO, обновляем информацию о NIC
            if success:
                print(f"Обновление информации о NIC {interface} после изменения TCXO")
                self.refresh_nic_info(interface)
            
            return success
                        
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
    
    def start_phc_sync(self, source_ptp: str, target_ptp: str) -> bool:
        """Запуск синхронизации между PHC часами"""
        try:
            print(f"Запуск синхронизации PHC: {source_ptp} -> {target_ptp}")
            
            # Команда для взаимной синхронизации
            cmd = [
                "sudo", "phc2sys", 
                "-s", source_ptp,  # источник
                "-c", target_ptp,  # цель
                "-O", "0",         # смещение 0
                "-R", "16",        # частота обновления 16 Гц
                "-m"               # вывод в консоль
            ]
            
            print(f"Выполняем команду: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ Синхронизация PHC запущена успешно")
                print(f"Вывод: {result.stdout}")
                return True
            else:
                print(f"❌ Ошибка запуска синхронизации PHC: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ Таймаут при запуске синхронизации PHC")
            return False
        except Exception as e:
            print(f"❌ Исключение при запуске синхронизации PHC: {e}")
            return False
    
    def stop_phc_sync(self) -> bool:
        """Остановка синхронизации PHC"""
        try:
            print("Остановка синхронизации PHC...")
            
            # Ищем и убиваем процессы phc2sys
            cmd = ["sudo", "pkill", "-f", "phc2sys"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ Синхронизация PHC остановлена")
                return True
            else:
                print(f"❌ Ошибка остановки синхронизации PHC: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при остановке синхронизации PHC: {e}")
            return False
    
    def start_ts2phc_sync(self, interface: str, ptp_device: str) -> bool:
        """Запуск синхронизации PHC по внешнему PPS"""
        try:
            print(f"Запуск ts2phc синхронизации для {interface}")
            
            # Этап 1: Проброс системного времени в PHC
            print(f"Этап 1: Проброс системного времени в PHC для {interface}")
            phc_ctl_cmd = ["sudo", "phc_ctl", interface, "set;", "adj", "37"]
            
            phc_result = subprocess.run(phc_ctl_cmd, capture_output=True, text=True, timeout=10)
            if phc_result.returncode == 0:
                print(f"✅ Системное время проброшено в PHC")
            else:
                print(f"⚠️ Предупреждение при пробросе времени: {phc_result.stderr}")
            
            # Этап 2: Запуск ts2phc для коррекции по внешнему PPS
            print(f"Этап 2: Запуск ts2phc для коррекции PHC по внешнему PPS")
            ts2phc_cmd = [
                "sudo", "ts2phc",
                "-c", ptp_device,           # коррекция времени на этом устройстве
                "-s", "generic",             # источник generic
                "--ts2phc.pin_index", "1",   # слушаем PPS на SDP1
                "-m",                        # вывод логов в консоль
                "-l", "7"                    # уровень детализации логов
            ]
            
            print(f"Выполняем команду: {' '.join(ts2phc_cmd)}")
            result = subprocess.run(ts2phc_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ ts2phc синхронизация запущена успешно")
                print(f"Вывод: {result.stdout}")
                return True
            else:
                print(f"❌ Ошибка запуска ts2phc: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ Таймаут при запуске ts2phc синхронизации")
            return False
        except Exception as e:
            print(f"❌ Исключение при запуске ts2phc синхронизации: {e}")
            return False
    
    def stop_ts2phc_sync(self) -> bool:
        """Остановка ts2phc синхронизации"""
        try:
            print("Остановка ts2phc синхронизации...")
            
            # Ищем и убиваем процессы ts2phc
            cmd = ["sudo", "pkill", "-f", "ts2phc"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ ts2phc синхронизация остановлена")
                return True
            else:
                print(f"❌ Ошибка остановки ts2phc: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при остановке ts2phc: {e}")
            return False
    
    def get_sync_status(self) -> Dict:
        """Получение статуса синхронизации"""
        try:
            status = {
                'phc2sys_running': False,
                'ts2phc_running': False,
                'phc2sys_pid': None,
                'ts2phc_pid': None
            }
            
            # Проверяем процессы phc2sys
            phc2sys_result = subprocess.run(["pgrep", "-f", "phc2sys"], 
                                          capture_output=True, text=True, timeout=5)
            if phc2sys_result.returncode == 0:
                status['phc2sys_running'] = True
                status['phc2sys_pid'] = phc2sys_result.stdout.strip()
            
            # Проверяем процессы ts2phc
            ts2phc_result = subprocess.run(["pgrep", "-f", "ts2phc"], 
                                         capture_output=True, text=True, timeout=5)
            if ts2phc_result.returncode == 0:
                status['ts2phc_running'] = True
                status['ts2phc_pid'] = ts2phc_result.stdout.strip()
            
            return status
            
        except Exception as e:
            print(f"Ошибка при получении статуса синхронизации: {e}")
            return {'phc2sys_running': False, 'ts2phc_running': False, 
                   'phc2sys_pid': None, 'ts2phc_pid': None}