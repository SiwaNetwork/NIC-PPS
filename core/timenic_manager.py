"""
TimeNIC Manager - модуль для работы с TimeNIC картами (Intel I226 NIC, SMA, TCXO)
Поддерживает PPS генерацию, прием внешних сигналов, синхронизацию PHC и PTM
"""

import os
import subprocess
import time
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class PPSMode(Enum):
    """Режимы работы PPS для TimeNIC"""
    DISABLED = "disabled"
    INPUT = "input"      # Прием внешнего PPS через SMA2 (SDP1)
    OUTPUT = "output"    # Генерация PPS через SMA1 (SDP0)
    BOTH = "both"        # Оба режима одновременно


class PTMStatus(Enum):
    """Статус PTM (PCIe Time Management)"""
    UNSUPPORTED = "unsupported"
    DISABLED = "disabled"
    ENABLED = "enabled"


@dataclass
class TimeNICInfo:
    """Информация о TimeNIC карте"""
    name: str
    mac_address: str
    ip_address: str
    status: str
    speed: str
    duplex: str
    pps_mode: PPSMode
    tcxo_enabled: bool
    ptm_status: PTMStatus
    ptp_device: Optional[str] = None
    phc_offset: Optional[int] = None
    phc_frequency: Optional[int] = None
    temperature: Optional[float] = None
    sma1_status: str = "disabled"  # SMA1 (SDP0) - выход PPS
    sma2_status: str = "disabled"  # SMA2 (SDP1) - вход PPS


@dataclass
class PTPInfo:
    """Информация о PTP устройстве"""
    device: str
    index: int
    name: str
    max_adj: int
    n_alarm: int
    n_ext_ts: int
    n_per_out: int
    n_pins: int
    pps: bool
    cross_timestamping: bool


class TimeNICManager:
    """Менеджер для работы с TimeNIC картами"""
    
    def __init__(self):
        self.timenic_list = []
        self.ptp_devices = []
        self.logger = logging.getLogger(__name__)
        self._discover_timenics()
        self._discover_ptp_devices()
    
    def _discover_timenics(self):
        """Обнаружение TimeNIC карт"""
        try:
            # Очищаем список перед новым обнаружением
            self.timenic_list = []
            
            # Получаем список всех сетевых интерфейсов
            interfaces = self._get_network_interfaces()
            
            for interface in interfaces:
                if self._is_timenic(interface):
                    timenic_info = self._get_timenic_info(interface)
                    if timenic_info:
                        self.timenic_list.append(timenic_info)
        except Exception as e:
            self.logger.error(f"Ошибка при обнаружении TimeNIC: {e}")
    
    def _discover_ptp_devices(self):
        """Обнаружение PTP устройств"""
        try:
            # Очищаем список перед новым обнаружением
            self.ptp_devices = []
            
            # Ищем PTP устройства в /dev/ptp*
            ptp_devices = list(Path("/dev").glob("ptp*"))
            
            for ptp_device in ptp_devices:
                ptp_info = self._get_ptp_info(str(ptp_device))
                if ptp_info:
                    self.ptp_devices.append(ptp_info)
        except Exception as e:
            self.logger.error(f"Ошибка при обнаружении PTP устройств: {e}")
    
    def _get_network_interfaces(self) -> List[str]:
        """Получение списка сетевых интерфейсов"""
        try:
            result = subprocess.run(["ip", "link", "show"], 
                                  capture_output=True, text=True, check=True)
            interfaces = []
            for line in result.stdout.split('\n'):
                if ':' in line and not line.startswith(' '):
                    interface = line.split(':')[1].strip()
                    if interface and not interface.startswith('lo'):
                        interfaces.append(interface)
            return interfaces
        except subprocess.CalledProcessError:
            return []
    
    def _is_timenic(self, interface: str) -> bool:
        """Проверка, является ли интерфейс TimeNIC картой"""
        try:
            # Проверяем драйвер igc (Intel I226)
            driver_path = f"/sys/class/net/{interface}/device/driver"
            if os.path.exists(driver_path):
                driver = os.path.basename(os.readlink(driver_path))
                return "igc" in driver
            
            # Проверяем через ethtool
            result = subprocess.run(["ethtool", "-i", interface], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return "igc" in result.stdout.lower()
        except:
            pass
        return False
    
    def _get_timenic_info(self, interface: str) -> Optional[TimeNICInfo]:
        """Получение информации о TimeNIC карте"""
        try:
            # Получаем MAC адрес
            mac = self._get_mac_address(interface)
            
            # Получаем IP адрес
            ip = self._get_ip_address(interface)
            
            # Получаем статус
            status = self._get_interface_status(interface)
            
            # Получаем скорость и дуплекс
            speed = self._get_interface_speed(interface)
            duplex = self._get_interface_duplex(interface)
            
            # Проверяем PPS режим
            pps_mode = self._get_pps_mode(interface)
            
            # Проверяем TCXO
            tcxo_enabled = self._is_tcxo_enabled(interface)
            
            # Проверяем PTM статус
            ptm_status = self._get_ptm_status(interface)
            
            # Находим связанное PTP устройство
            ptp_device = self._find_ptp_device_for_interface(interface)
            
            # Получаем информацию о PHC
            phc_offset, phc_frequency = self._get_phc_info(ptp_device)
            
            # Получаем температуру
            temperature = self._get_temperature(interface)
            
            # Получаем статус SMA разъемов
            sma1_status = self._get_sma1_status(interface)
            sma2_status = self._get_sma2_status(interface)
            
            return TimeNICInfo(
                name=interface,
                mac_address=mac,
                ip_address=ip,
                status=status,
                speed=speed,
                duplex=duplex,
                pps_mode=pps_mode,
                tcxo_enabled=tcxo_enabled,
                ptm_status=ptm_status,
                ptp_device=ptp_device,
                phc_offset=phc_offset,
                phc_frequency=phc_frequency,
                temperature=temperature,
                sma1_status=sma1_status,
                sma2_status=sma2_status
            )
        except Exception as e:
            self.logger.error(f"Ошибка при получении информации о TimeNIC {interface}: {e}")
            return None
    
    def _get_ptp_info(self, ptp_device: str) -> Optional[PTPInfo]:
        """Получение информации о PTP устройстве"""
        try:
            # Используем testptp для получения информации
            result = subprocess.run(["testptp", "-d", ptp_device, "-q"], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                return None
            
            # Парсим вывод testptp
            lines = result.stdout.split('\n')
            info = {}
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip()] = value.strip()
            
            return PTPInfo(
                device=ptp_device,
                index=int(info.get('index', 0)),
                name=info.get('name', ''),
                max_adj=int(info.get('max_adj', 0)),
                n_alarm=int(info.get('n_alarm', 0)),
                n_ext_ts=int(info.get('n_ext_ts', 0)),
                n_per_out=int(info.get('n_per_out', 0)),
                n_pins=int(info.get('n_pins', 0)),
                pps=info.get('pps', '0') == '1',
                cross_timestamping=info.get('cross_timestamping', '0') == '1'
            )
        except Exception as e:
            self.logger.error(f"Ошибка при получении информации о PTP {ptp_device}: {e}")
            return None
    
    def _get_mac_address(self, interface: str) -> str:
        """Получение MAC адреса интерфейса"""
        try:
            result = subprocess.run(["ip", "link", "show", interface], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'link/ether' in line:
                        return line.split()[1]
        except:
            pass
        return ""
    
    def _get_ip_address(self, interface: str) -> str:
        """Получение IP адреса интерфейса"""
        try:
            result = subprocess.run(["ip", "addr", "show", interface], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'inet ' in line:
                        return line.split()[1].split('/')[0]
        except:
            pass
        return ""
    
    def _get_interface_status(self, interface: str) -> str:
        """Получение статуса интерфейса"""
        try:
            if os.path.exists(f"/sys/class/net/{interface}/carrier"):
                return "up"
            return "down"
        except:
            return "unknown"
    
    def _get_interface_speed(self, interface: str) -> str:
        """Получение скорости интерфейса"""
        try:
            result = subprocess.run(["ethtool", interface], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Speed:' in line:
                        return line.split(':')[1].strip()
        except:
            pass
        return "unknown"
    
    def _get_interface_duplex(self, interface: str) -> str:
        """Получение режима дуплекса"""
        try:
            result = subprocess.run(["ethtool", interface], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Duplex:' in line:
                        return line.split(':')[1].strip()
        except:
            pass
        return "unknown"
    
    def _get_pps_mode(self, interface: str) -> PPSMode:
        """Получение текущего режима PPS"""
        try:
            # Проверяем через testptp если есть PTP устройство
            ptp_device = self._find_ptp_device_for_interface(interface)
            if ptp_device:
                result = subprocess.run(["testptp", "-d", ptp_device, "-q"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    # Анализируем вывод для определения режима
                    if "n_per_out: 1" in result.stdout and "n_ext_ts: 1" in result.stdout:
                        return PPSMode.BOTH
                    elif "n_per_out: 1" in result.stdout:
                        return PPSMode.OUTPUT
                    elif "n_ext_ts: 1" in result.stdout:
                        return PPSMode.INPUT
        except:
            pass
        return PPSMode.DISABLED
    
    def _is_tcxo_enabled(self, interface: str) -> bool:
        """Проверка включения TCXO"""
        try:
            # Проверяем через sysfs или драйвер
            tcxo_path = f"/sys/class/net/{interface}/device/tcxo_enabled"
            if os.path.exists(tcxo_path):
                with open(tcxo_path, 'r') as f:
                    return f.read().strip() == '1'
        except:
            pass
        return False
    
    def _get_ptm_status(self, interface: str) -> PTMStatus:
        """Получение статуса PTM"""
        try:
            # Проверяем через lspci
            result = subprocess.run(["lspci", "-vvv"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Ищем строки с PTM
                if "Precision Time Measurement" in result.stdout:
                    return PTMStatus.ENABLED
        except:
            pass
        return PTMStatus.UNSUPPORTED
    
    def _find_ptp_device_for_interface(self, interface: str) -> Optional[str]:
        """Поиск PTP устройства для интерфейса"""
        try:
            # Проверяем через ethtool -T
            result = subprocess.run(["ethtool", "-T", interface], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'PTP Hardware Clock:' in line:
                        clock_id = line.split(':')[1].strip()
                        ptp_device = f"/dev/ptp{clock_id}"
                        if os.path.exists(ptp_device):
                            return ptp_device
        except:
            pass
        return None
    
    def _get_phc_info(self, ptp_device: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
        """Получение информации о PHC"""
        if not ptp_device:
            return None, None
        
        try:
            # Используем phc_ctl для получения информации
            result = subprocess.run(["phc_ctl", ptp_device, "get"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Парсим вывод для получения offset и frequency
                lines = result.stdout.split('\n')
                offset = None
                frequency = None
                
                for line in lines:
                    if 'offset' in line:
                        offset = int(line.split()[1])
                    elif 'frequency' in line:
                        frequency = int(line.split()[1])
                
                return offset, frequency
        except:
            pass
        return None, None
    
    def _get_temperature(self, interface: str) -> Optional[float]:
        """Получение температуры карты"""
        try:
            # Проверяем различные пути к датчику температуры
            temp_paths = [
                f"/sys/class/net/{interface}/device/hwmon/hwmon*/temp1_input",
                f"/sys/class/net/{interface}/device/temperature"
            ]
            
            for temp_path in temp_paths:
                if os.path.exists(temp_path):
                    with open(temp_path, 'r') as f:
                        temp_raw = int(f.read().strip())
                        return temp_raw / 1000.0  # Конвертируем в градусы Цельсия
        except:
            pass
        return None
    
    def _get_sma1_status(self, interface: str) -> str:
        """Получение статуса SMA1 (SDP0) - выход PPS"""
        try:
            ptp_device = self._find_ptp_device_for_interface(interface)
            if ptp_device:
                # Проверяем через testptp
                result = subprocess.run(["testptp", "-d", ptp_device, "-q"], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and "n_per_out: 1" in result.stdout:
                    return "enabled"
        except:
            pass
        return "disabled"
    
    def _get_sma2_status(self, interface: str) -> str:
        """Получение статуса SMA2 (SDP1) - вход PPS"""
        try:
            ptp_device = self._find_ptp_device_for_interface(interface)
            if ptp_device:
                # Проверяем через testptp
                result = subprocess.run(["testptp", "-d", ptp_device, "-q"], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and "n_ext_ts: 1" in result.stdout:
                    return "enabled"
        except:
            pass
        return "disabled"
    
    def get_all_timenics(self) -> List[TimeNICInfo]:
        """Получение списка всех TimeNIC карт"""
        return self.timenic_list
    
    def get_timenic_by_name(self, name: str) -> Optional[TimeNICInfo]:
        """Получение TimeNIC карты по имени"""
        for timenic in self.timenic_list:
            if timenic.name == name:
                return timenic
        return None
    
    def get_all_ptp_devices(self) -> List[PTPInfo]:
        """Получение списка всех PTP устройств"""
        return self.ptp_devices
    
    def refresh(self):
        """Обновление списка TimeNIC карт и PTP устройств"""
        self._discover_timenics()
        self._discover_ptp_devices()
    
    def set_pps_mode(self, interface: str, mode: PPSMode) -> bool:
        """Установка режима PPS для TimeNIC"""
        try:
            timenic = self.get_timenic_by_name(interface)
            if not timenic or not timenic.ptp_device:
                self.logger.error(f"PTP устройство не найдено для {interface}")
                return False
            
            ptp_device = timenic.ptp_device
            
            if mode == PPSMode.DISABLED:
                return self._disable_pps(ptp_device)
            elif mode == PPSMode.INPUT:
                return self._enable_pps_input(ptp_device)
            elif mode == PPSMode.OUTPUT:
                return self._enable_pps_output(ptp_device)
            elif mode == PPSMode.BOTH:
                return self._enable_pps_both(ptp_device)
            
        except Exception as e:
            self.logger.error(f"Ошибка при установке PPS режима: {e}")
            return False
    
    def _disable_pps(self, ptp_device: str) -> bool:
        """Отключение PPS"""
        try:
            # Отключаем периодический выход (SDP0)
            subprocess.run(["testptp", "-d", ptp_device, "-L0,0"], check=True)
            # Отключаем внешние временные метки (SDP1)
            subprocess.run(["testptp", "-d", ptp_device, "-L1,0"], check=True)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ошибка при отключении PPS: {e}")
            return False
    
    def _enable_pps_output(self, ptp_device: str) -> bool:
        """Включение PPS выхода (SMA1/SDP0)"""
        try:
            # Настраиваем SDP0 как выходной пин для периодического сигнала
            # Согласно гайду: -L0,2 где 0 - индекс SDP0, 2 - функция "periodic output"
            subprocess.run(["testptp", "-d", ptp_device, "-L0,2"], check=True)
            # Устанавливаем период 1 Гц (1 секунда = 1000000000 наносекунд)
            subprocess.run(["testptp", "-d", ptp_device, "-p", "1000000000"], check=True)
            self.logger.info(f"PPS выход включен на {ptp_device} (SMA1/SDP0)")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ошибка при включении PPS выхода: {e}")
            return False
    
    def _enable_pps_input(self, ptp_device: str) -> bool:
        """Включение PPS входа (SMA2/SDP1)"""
        try:
            # Настраиваем SDP1 как входной пин для внешних временных меток
            # Согласно гайду: -L1,1 где 1 - индекс SDP1, 1 - функция EXTTS
            subprocess.run(["testptp", "-d", ptp_device, "-L1,1"], check=True)
            self.logger.info(f"PPS вход включен на {ptp_device} (SMA2/SDP1)")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ошибка при включении PPS входа: {e}")
            return False
    
    def _enable_pps_both(self, ptp_device: str) -> bool:
        """Включение PPS входа и выхода одновременно"""
        try:
            # Включаем выход
            if not self._enable_pps_output(ptp_device):
                return False
            # Включаем вход
            if not self._enable_pps_input(ptp_device):
                return False
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при включении PPS входа и выхода: {e}")
            return False
    
    def set_tcxo_enabled(self, interface: str, enabled: bool) -> bool:
        """Управление TCXO"""
        try:
            tcxo_path = f"/sys/class/net/{interface}/device/tcxo_enabled"
            if os.path.exists(tcxo_path):
                with open(tcxo_path, 'w') as f:
                    f.write('1' if enabled else '0')
                return True
        except Exception as e:
            self.logger.error(f"Ошибка при управлении TCXO: {e}")
            return False
        return False
    
    def start_phc_synchronization(self, interface: str) -> bool:
        """Запуск синхронизации PHC по внешнему PPS"""
        try:
            timenic = self.get_timenic_by_name(interface)
            if not timenic or not timenic.ptp_device:
                return False
            
            # Запускаем ts2phc для коррекции PHC по внешнему PPS
            cmd = [
                "ts2phc",
                "-c", timenic.ptp_device,
                "-s", "generic",
                "--ts2phc.pin_index", "1",  # SDP1
                "-m",  # Вывод логов в консоль
                "-l", "7"  # Уровень детализации логов
            ]
            
            # Запускаем в фоне
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при запуске синхронизации PHC: {e}")
            return False
    
    def enable_ptm(self, interface: str) -> bool:
        """Включение PTM для TimeNIC"""
        try:
            # Находим PCI адрес карты
            result = subprocess.run(["lspci", "-nn"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Ethernet controller' in line and 'Intel' in line:
                        # Извлекаем PCI адрес
                        pci_addr = line.split()[0]
                        ptm_path = f"/sys/bus/pci/devices/0000:{pci_addr}/enable_ptm"
                        if os.path.exists(ptm_path):
                            with open(ptm_path, 'w') as f:
                                f.write('1')
                            return True
        except Exception as e:
            self.logger.error(f"Ошибка при включении PTM: {e}")
            return False
        return False
    
    def read_pps_events(self, ptp_device: str, count: int = 5) -> List[Dict[str, Any]]:
        """Чтение PPS событий с внешнего источника
        
        Args:
            ptp_device: PTP устройство (например, /dev/ptp0)
            count: Количество событий для чтения
            
        Returns:
            Список событий с временными метками
        """
        try:
            # Читаем события используя testptp -e
            result = subprocess.run(
                ["testptp", "-d", ptp_device, "-e", str(count)],
                capture_output=True, text=True, timeout=count + 2
            )
            
            if result.returncode != 0:
                self.logger.error(f"Ошибка чтения PPS событий: {result.stderr}")
                return []
            
            events = []
            for line in result.stdout.split('\n'):
                if 'event' in line and 'index' in line:
                    # Парсим строку события
                    # Пример: event index 1 at 1234567890.123456789
                    parts = line.split()
                    if len(parts) >= 6:
                        event = {
                            'index': int(parts[2]),
                            'timestamp': parts[4]
                        }
                        events.append(event)
            
            return events
            
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Таймаут при чтении {count} PPS событий")
            return []
        except Exception as e:
            self.logger.error(f"Ошибка при чтении PPS событий: {e}")
            return []
    
    def set_pps_period(self, ptp_device: str, period_ns: int) -> bool:
        """Установка периода PPS сигнала
        
        Args:
            ptp_device: PTP устройство (например, /dev/ptp0)
            period_ns: Период в наносекундах (1000000000 = 1 Гц)
            
        Returns:
            True если успешно
        """
        try:
            # Устанавливаем период используя testptp -p
            subprocess.run(
                ["testptp", "-d", ptp_device, "-p", str(period_ns)],
                check=True
            )
            self.logger.info(f"Период PPS установлен: {period_ns} нс на {ptp_device}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ошибка при установке периода PPS: {e}")
            return False
    
    def sync_phc_to_system_time(self, interface: str) -> bool:
        """Синхронизация PHC с системным временем
        
        Использует phc_ctl для установки текущего системного времени в PHC
        """
        try:
            # Используем phc_ctl "set;" adj 37 согласно гайду
            subprocess.run(
                ["phc_ctl", interface, "set;", "adj", "37"],
                check=True
            )
            self.logger.info(f"PHC синхронизирован с системным временем на {interface}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ошибка при синхронизации PHC: {e}")
            return False
    
    def get_statistics(self, interface: str) -> Dict[str, Any]:
        """Получение статистики TimeNIC карты"""
        try:
            timenic = self.get_timenic_by_name(interface)
            if not timenic:
                return {}
            
            stats = {
                'interface': interface,
                'status': timenic.status,
                'speed': timenic.speed,
                'duplex': timenic.duplex,
                'pps_mode': timenic.pps_mode.value,
                'tcxo_enabled': timenic.tcxo_enabled,
                'ptm_status': timenic.ptm_status.value,
                'sma1_status': timenic.sma1_status,
                'sma2_status': timenic.sma2_status,
                'temperature': timenic.temperature,
                'phc_offset': timenic.phc_offset,
                'phc_frequency': timenic.phc_frequency
            }
            
            # Получаем статистику сети
            try:
                result = subprocess.run(["cat", f"/sys/class/net/{interface}/statistics/rx_bytes"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    stats['rx_bytes'] = int(result.stdout.strip())
                
                result = subprocess.run(["cat", f"/sys/class/net/{interface}/statistics/tx_bytes"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    stats['tx_bytes'] = int(result.stdout.strip())
                    
                result = subprocess.run(["cat", f"/sys/class/net/{interface}/statistics/rx_packets"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    stats['rx_packets'] = int(result.stdout.strip())
                
                result = subprocess.run(["cat", f"/sys/class/net/{interface}/statistics/tx_packets"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    stats['tx_packets'] = int(result.stdout.strip())
                    
                result = subprocess.run(["cat", f"/sys/class/net/{interface}/statistics/rx_errors"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    stats['rx_errors'] = int(result.stdout.strip())
                
                result = subprocess.run(["cat", f"/sys/class/net/{interface}/statistics/tx_errors"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    stats['tx_errors'] = int(result.stdout.strip())
            except:
                pass
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики: {e}")
            return {}
    
    def monitor_traffic(self, interface: str, callback=None, interval: int = 1):
        """Мониторинг трафика в реальном времени
        
        Args:
            interface: имя интерфейса
            callback: функция обратного вызова для обработки данных
            interval: интервал обновления в секундах
        """
        try:
            prev_stats = self.get_statistics(interface)
            prev_time = time.time()
            
            while True:
                time.sleep(interval)
                current_stats = self.get_statistics(interface)
                current_time = time.time()
                time_diff = current_time - prev_time
                
                # Вычисляем скорость
                if 'rx_bytes' in current_stats and 'rx_bytes' in prev_stats:
                    rx_speed = (current_stats['rx_bytes'] - prev_stats['rx_bytes']) / time_diff
                    current_stats['rx_speed'] = rx_speed
                    
                if 'tx_bytes' in current_stats and 'tx_bytes' in prev_stats:
                    tx_speed = (current_stats['tx_bytes'] - prev_stats['tx_bytes']) / time_diff
                    current_stats['tx_speed'] = tx_speed
                    
                if 'rx_packets' in current_stats and 'rx_packets' in prev_stats:
                    rx_pps = (current_stats['rx_packets'] - prev_stats['rx_packets']) / time_diff
                    current_stats['rx_pps'] = rx_pps
                    
                if 'tx_packets' in current_stats and 'tx_packets' in prev_stats:
                    tx_pps = (current_stats['tx_packets'] - prev_stats['tx_packets']) / time_diff
                    current_stats['tx_pps'] = tx_pps
                
                # Обновляем информацию о TimeNIC
                self.refresh()
                timenic = self.get_timenic_by_name(interface)
                if timenic:
                    current_stats.update({
                        'phc_offset': timenic.phc_offset,
                        'phc_frequency': timenic.phc_frequency,
                        'temperature': timenic.temperature
                    })
                
                if callback:
                    callback(current_stats)
                
                prev_stats = current_stats
                prev_time = current_time
                
        except KeyboardInterrupt:
            self.logger.info("Мониторинг остановлен пользователем")
        except Exception as e:
            self.logger.error(f"Ошибка при мониторинге трафика: {e}")
    
    def install_timenic_driver(self) -> bool:
        """Установка драйвера TimeNIC с патчем для PPS"""
        try:
            # Скачиваем драйвер
            subprocess.run(["wget", "https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip"], 
                          check=True)
            
            # Распаковываем
            subprocess.run(["unzip", "intel-igc-ppsfix_ubuntu.zip"], check=True)
            
            # Удаляем старый драйвер
            subprocess.run(["dkms", "remove", "igc", "-v", "5.4.0-7642.46"], 
                          capture_output=True)
            
            # Добавляем и собираем новый драйвер
            subprocess.run(["dkms", "add", "."], check=True)
            subprocess.run(["dkms", "build", "--force", "igc", "-v", "5.4.0-7642.46"], check=True)
            subprocess.run(["dkms", "install", "--force", "igc", "-v", "5.4.0-7642.46"], check=True)
            
            # Заменяем оригинальный модуль
            kernel_version = subprocess.run(["uname", "-r"], capture_output=True, text=True).stdout.strip()
            subprocess.run(["cp", f"/lib/modules/{kernel_version}/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst",
                          f"/lib/modules/{kernel_version}/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst.bak"], check=True)
            subprocess.run(["cp", f"/lib/modules/{kernel_version}/updates/dkms/igc.ko.zst",
                          f"/lib/modules/{kernel_version}/kernel/drivers/net/ethernet/intel/igc/"], check=True)
            
            # Обновляем initramfs
            subprocess.run(["depmod", "-a"], check=True)
            subprocess.run(["update-initramfs", "-u"], check=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ошибка при установке драйвера TimeNIC: {e}")
            return False
    
    def create_systemd_service(self) -> bool:
        """Создание systemd сервиса для автозапуска"""
        try:
            service_content = """[Unit]
Description=Setup PTP on TimeNIC PCIe card
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes

ExecStart=/usr/bin/testptp -d /dev/ptp0 -L0,2
ExecStart=/usr/bin/testptp -d /dev/ptp0 -p 1000000000
ExecStart=/usr/bin/testptp -d /dev/ptp0 -L1,1
ExecStart=/usr/sbin/ts2phc -c /dev/ptp0 -s generic --ts2phc.pin_index 1 -m -l 7

[Install]
WantedBy=multi-user.target
"""
            
            with open("/etc/systemd/system/ptp-nic-setup.service", "w") as f:
                f.write(service_content)
            
            # Активируем сервис
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "enable", "ptp-nic-setup"], check=True)
            subprocess.run(["systemctl", "start", "ptp-nic-setup"], check=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании systemd сервиса: {e}")
            return False