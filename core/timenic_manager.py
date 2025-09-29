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
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Импорт модуля фильтрации PPS событий
from .pps_edge_filter import pps_manager, PPSEvent, PPSEventType


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
        self.timenics = []  # Исправлено: используем timenics вместо timenic_list
        self.ptp_devices = []
        self.logger = logging.getLogger(__name__)
        self._discover_timenics()
        self._discover_ptp_devices()
    
    def _discover_timenics(self):
        """Обнаружение TimeNIC карт"""
        try:
            # Очищаем список перед новым обнаружением
            self.timenics = []  # Исправлено: используем timenics вместо timenic_list
            
            # Получаем список всех сетевых интерфейсов
            interfaces = self._get_network_interfaces()
            
            for interface in interfaces:
                if self._is_timenic(interface):
                    timenic_info = self._get_timenic_info(interface)
                    if timenic_info:
                        self.timenics.append(timenic_info)  # Исправлено: используем timenics
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
                                  capture_output=True, text=True, check=True, timeout=10)
            interfaces = []
            for line in result.stdout.split('\n'):
                if ':' in line and not line.startswith(' '):
                    interface = line.split(':')[1].strip()
                    if interface and not interface.startswith('lo'):
                        interfaces.append(interface)
            return interfaces
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to netifaces
            try:
                import netifaces
                return [iface for iface in netifaces.interfaces() if not iface.startswith('lo')]
            except Exception:
                return []
    
    def _is_timenic(self, interface: str) -> bool:
        """Проверка, является ли интерфейс TimeNIC картой"""
        try:
            # Проверяем драйвер igc (Intel I226) или igb (Intel I210)
            driver_path = f"/sys/class/net/{interface}/device/driver"
            if os.path.exists(driver_path):
                driver = os.path.basename(os.readlink(driver_path))
                return "igc" in driver.lower() or "igb" in driver.lower()
            
            # Проверяем через ethtool
            result = subprocess.run(["ethtool", "-i", interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return "igc" in result.stdout.lower() or "igb" in result.stdout.lower()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception):
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
                                  capture_output=True, text=True, timeout=10)
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.error(f"Ошибка при получении информации о PTP {ptp_device}: {e}")
            return None
    
    def _get_mac_address(self, interface: str) -> str:
        """Получение MAC адреса интерфейса"""
        try:
            result = subprocess.run(["ip", "link", "show", interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'link/ether' in line:
                        return line.split()[1]
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return ""
    
    def _get_ip_address(self, interface: str) -> str:
        """Получение IP адреса интерфейса"""
        try:
            result = subprocess.run(["ip", "addr", "show", interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'inet ' in line:
                        return line.split()[1].split('/')[0]
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return ""
    
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
            result = subprocess.run(["ethtool", interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Speed:' in line:
                        return line.split(':')[1].strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return "unknown"
    
    def _get_interface_duplex(self, interface: str) -> str:
        """Получение режима дуплекса"""
        try:
            result = subprocess.run(["ethtool", interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Duplex:' in line:
                        return line.split(':')[1].strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return "unknown"
    
    def _get_pps_mode(self, interface: str) -> PPSMode:
        """Получение текущего режима PPS"""
        try:
            # Проверяем через testptp если есть PTP устройство
            ptp_device = self._find_ptp_device_for_interface(interface)
            if ptp_device:
                result = subprocess.run(["testptp", "-d", ptp_device, "-q"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # Анализируем вывод для определения режима
                    if "n_per_out: 1" in result.stdout and "n_ext_ts: 1" in result.stdout:
                        return PPSMode.BOTH
                    elif "n_per_out: 1" in result.stdout:
                        return PPSMode.OUTPUT
                    elif "n_ext_ts: 1" in result.stdout:
                        return PPSMode.INPUT
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception):
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception):
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        return PTMStatus.UNSUPPORTED
    
    def _find_ptp_device_for_interface(self, interface: str) -> Optional[str]:
        """Поиск PTP устройства для интерфейса"""
        try:
            # Проверяем через ethtool -T
            result = subprocess.run(["ethtool", "-T", interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'PTP Hardware Clock:' in line:
                        clock_id = line.split(':')[1].strip()
                        ptp_device = f"/dev/ptp{clock_id}"
                        if os.path.exists(ptp_device):
                            return ptp_device
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        return None
    
    def _get_phc_info(self, ptp_device: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
        """Получение информации о PHC"""
        if not ptp_device:
            return None, None
        
        try:
            # Используем phc_ctl для получения информации
            result = subprocess.run(["phc_ctl", ptp_device, "get"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Парсим вывод для получения offset и frequency
                lines = result.stdout.split('\n')
                offset = None
                frequency = None
                
                for line in lines:
                    if 'offset' in line:
                        try:
                            offset = int(line.split()[1])
                        except (IndexError, ValueError):
                            pass
                    elif 'frequency' in line:
                        try:
                            frequency = int(line.split()[1])
                        except (IndexError, ValueError):
                            pass
                
                return offset, frequency
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception):
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception):
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception):
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        return "disabled"
    
    def get_all_timenics(self) -> List[TimeNICInfo]:
        """Получение списка всех TimeNIC карт"""
        return self.timenics
    
    def get_timenic_by_name(self, name: str) -> Optional[TimeNICInfo]:
        """Получение TimeNIC карты по имени"""
        for timenic in self.timenics:
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
            if not timenic:
                self.logger.error(f"TimeNIC карта не найдена для интерфейса {interface}")
                self.logger.info("Доступные TimeNIC карты:")
                for t in self.timenics:
                    self.logger.info(f"  - {t.name}")
                return False
            
            if not timenic.ptp_device:
                self.logger.error(f"PTP устройство не найдено для {interface}")
                self.logger.info("Проверьте:")
                self.logger.info("  1. Драйвер igc загружен: lsmod | grep igc")
                self.logger.info("  2. PTP поддержка включена: ethtool -T " + interface)
                self.logger.info("  3. PTP устройства существуют: ls /dev/ptp*")
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.error(f"Ошибка при включении PPS выхода: {e}")
            return False
    
    def _enable_pps_input(self, ptp_device: str) -> bool:
        """Включение PPS входа (SMA2/SDP1) с настройкой фронта"""
        try:
            # Настраиваем SDP1 как входной пин для внешних временных меток
            # Согласно гайду: -L1,1 где 1 - индекс SDP1, 1 - функция EXTTS
            subprocess.run(["testptp", "-d", ptp_device, "-L1,1"], check=True)
            
            # Дополнительно настраиваем для использования только восходящего фронта
            # Это помогает избежать двойных событий от заднего фронта
            try:
                # Проверяем текущую конфигурацию
                result = subprocess.run(["testptp", "-d", ptp_device, "-l"], 
                                      capture_output=True, text=True, check=True)
                self.logger.info(f"Текущая конфигурация PPS: {result.stdout}")
                
                # Если доступно, настраиваем фронт через sysfs
                self._configure_pps_edge_detection(ptp_device)
                
            except Exception as edge_e:
                self.logger.warning(f"Не удалось настроить фронт PPS: {edge_e}")
            
            self.logger.info(f"PPS вход включен на {ptp_device} (SMA2/SDP1) с настройкой фронта")
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.error(f"Ошибка при управлении TCXO: {e}")
            return False
        return False
    
    def _configure_pps_edge_detection(self, ptp_device: str) -> bool:
        """Настройка детекции фронтов PPS для избежания двойных событий"""
        try:
            # Пытаемся найти sysfs интерфейс для настройки фронтов
            # Это зависит от конкретной реализации драйвера
            ptp_num = ptp_device.split('/dev/ptp')[1] if '/dev/ptp' in ptp_device else '0'
            
            # Возможные пути для настройки фронтов
            edge_paths = [
                f"/sys/class/ptp/ptp{ptp_num}/extts_flags",
                f"/sys/class/ptp/ptp{ptp_num}/pin_config",
                f"/sys/class/ptp/ptp{ptp_num}/extts_enable"
            ]
            
            for path in edge_paths:
                if os.path.exists(path):
                    try:
                        # Пытаемся установить флаг для восходящего фронта
                        with open(path, 'w') as f:
                            f.write('1')  # RISING_EDGE
                        self.logger.info(f"Настроен восходящий фронт PPS через {path}")
                        return True
                    except Exception as e:
                        self.logger.debug(f"Не удалось настроить {path}: {e}")
                        continue
            
            # Альтернативный способ через testptp
            try:
                # Некоторые версии testptp поддерживают настройку фронтов
                result = subprocess.run(
                    ["testptp", "-d", ptp_device, "-L1,1", "-E1"],  # -E1 для восходящего фронта
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    self.logger.info("Настроен восходящий фронт PPS через testptp")
                    return True
            except Exception as e:
                self.logger.debug(f"testptp настройка фронта не поддерживается: {e}")
            
            self.logger.warning("Не удалось настроить фронт PPS - возможны двойные события")
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка при настройке фронтов PPS: {e}")
            return False
    
    def start_pps_monitoring(self, ptp_device: str, callback=None) -> bool:
        """Запуск мониторинга PPS событий в реальном времени с фильтрацией
        
        Args:
            ptp_device: PTP устройство
            callback: Функция обратного вызова для обработки событий
            
        Returns:
            True если мониторинг запущен успешно
        """
        try:
            # Создаем монитор если его нет
            if ptp_device not in pps_manager.monitors:
                monitor = pps_manager.create_monitor(ptp_device, pin_index=1)
            else:
                monitor = pps_manager.monitors[ptp_device]
            
            # Запускаем мониторинг
            monitor.start_monitoring(callback)
            self.logger.info(f"Запущен мониторинг PPS событий для {ptp_device}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при запуске мониторинга PPS: {e}")
            return False
    
    def stop_pps_monitoring(self, ptp_device: str) -> bool:
        """Остановка мониторинга PPS событий
        
        Args:
            ptp_device: PTP устройство
            
        Returns:
            True если мониторинг остановлен успешно
        """
        try:
            pps_manager.stop_monitoring(ptp_device)
            self.logger.info(f"Остановлен мониторинг PPS событий для {ptp_device}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при остановке мониторинга PPS: {e}")
            return False
    
    def get_pps_statistics(self, ptp_device: str) -> Dict[str, Any]:
        """Получение статистики PPS мониторинга
        
        Args:
            ptp_device: PTP устройство
            
        Returns:
            Словарь со статистикой
        """
        try:
            if ptp_device in pps_manager.monitors:
                return pps_manager.monitors[ptp_device].get_statistics()
            else:
                return {'error': 'Монитор не найден'}
                
        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики PPS: {e}")
            return {'error': str(e)}
    
    def _validate_offset(self, offset_ns: int) -> bool:
        """Валидация значения offset
        
        Args:
            offset_ns: Задержка в наносекундах
            
        Returns:
            True если значение валидно
        """
        # Ограничиваем offset разумными пределами: ±1 секунда
        MAX_OFFSET_NS = 1_000_000_000  # 1 секунда
        MIN_OFFSET_NS = -1_000_000_000  # -1 секунда
        
        if offset_ns < MIN_OFFSET_NS or offset_ns > MAX_OFFSET_NS:
            self.logger.error(f"Offset {offset_ns} нс выходит за допустимые пределы (±1 с)")
            return False
        
        return True

    def start_phc_synchronization(self, interface: str, offset_ns: int = 0) -> bool:
        """Запуск синхронизации PHC по внешнему PPS с настраиваемой задержкой
        
        Args:
            interface: Имя интерфейса TimeNIC
            offset_ns: Задержка в наносекундах (положительная или отрицательная)
        """
        try:
            # Валидируем offset
            if not self._validate_offset(offset_ns):
                return False
            
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
            
            # Добавляем offset если указан
            if offset_ns != 0:
                cmd.extend(["--ts2phc.offset", str(offset_ns)])
                self.logger.info(f"Применяется задержка {offset_ns} нс для {interface}")
            
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.error(f"Ошибка при включении PTM: {e}")
            return False
        return False
    
    def disable_ptm(self, interface: str) -> bool:
        """Отключение PTM для TimeNIC"""
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
                                f.write('0')
                            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.error(f"Ошибка при отключении PTM: {e}")
            return False
        return False

    def set_ptm(self, interface: str, enabled: bool, master: bool = False) -> bool:
        """Унифицированный метод управления PTM
        
        Args:
            interface: сетевой интерфейс
            enabled: включить или выключить PTM
            master: зарезервировано для расширений; пока не используется
        """
        try:
            if enabled:
                return self.enable_ptm(interface)
            else:
                return self.disable_ptm(interface)
        except Exception as e:
            self.logger.error(f"Ошибка при установке PTM: {e}")
            return False
    
    def read_pps_events(self, ptp_device: str, count: int = 5) -> List[Dict[str, Any]]:
        """Чтение PPS событий с внешнего источника с автоматической фильтрацией
        
        Args:
            ptp_device: PTP устройство (например, /dev/ptp0)
            count: Количество событий для чтения
            
        Returns:
            Список отфильтрованных событий с временными метками
        """
        try:
            # Создаем монитор если его нет
            if ptp_device not in pps_manager.monitors:
                monitor = pps_manager.create_monitor(ptp_device, pin_index=1)
            else:
                monitor = pps_manager.monitors[ptp_device]
            
            # Читаем события с фильтрацией
            filtered_events = []
            attempts = 0
            max_attempts = count * 3  # Учитываем возможные двойные события
            
            while len(filtered_events) < count and attempts < max_attempts:
                # Читаем сырые события
                raw_events = monitor._read_pps_events(count=count, timeout=2)
                
                for raw_event in raw_events:
                    if len(filtered_events) >= count:
                        break
                    
                    # Парсим и фильтруем событие
                    parsed_event = monitor._parse_event(raw_event)
                    if parsed_event:
                        filtered_event = monitor.filter.filter_event(parsed_event)
                        if filtered_event:
                            filtered_events.append({
                                'index': filtered_event.pin_index,
                                'timestamp': str(filtered_event.timestamp),
                                'event_type': filtered_event.event_type.value,
                                'raw_data': filtered_event.raw_data
                            })
                
                attempts += 1
                if len(filtered_events) < count:
                    time.sleep(0.1)  # Небольшая задержка между попытками
            
            # Логируем статистику фильтрации
            stats = monitor.get_statistics()
            if stats['total_events'] > 0:
                self.logger.info(f"PPS фильтрация: {stats['valid_events']}/{stats['total_events']} событий прошли фильтр "
                               f"({stats['filter_rate']:.1f}% отфильтровано)")
            
            return filtered_events
            
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.error(f"Ошибка при установке периода PPS: {e}")
            return False
    
    def sync_phc_to_system_time(self, interface: str, offset_ns: int = 0) -> bool:
        """Синхронизация PHC с системным временем с настраиваемой задержкой
        
        Args:
            interface: Имя интерфейса TimeNIC
            offset_ns: Задержка в наносекундах (положительная или отрицательная)
        """
        try:
            # Валидируем offset
            if not self._validate_offset(offset_ns):
                return False
            
            # Используем phc_ctl "set;" adj 37 согласно гайду
            cmd = ["phc_ctl", interface, "set;", "adj", "37"]
            
            # Если указана задержка, применяем её
            if offset_ns != 0:
                # phc_ctl не поддерживает offset напрямую, поэтому используем adjtimex
                # Сначала устанавливаем время, затем корректируем
                subprocess.run(cmd, check=True)
                
                # Применяем offset через adjtimex
                offset_sec = offset_ns / 1_000_000_000.0
                adj_cmd = ["phc_ctl", interface, "adj", str(int(offset_sec * 1_000_000))]  # в микросекундах
                subprocess.run(adj_cmd, check=True)
                
                self.logger.info(f"PHC синхронизирован с системным временем на {interface} с задержкой {offset_ns} нс")
            else:
                subprocess.run(cmd, check=True)
                self.logger.info(f"PHC синхронизирован с системным временем на {interface}")
            
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.error(f"Ошибка при синхронизации PHC: {e}")
            return False
    
    def start_phc_to_phc_sync(self, source_ptp: str, target_ptp: str, offset_ns: int = 0, rate: float = 0.0) -> bool:
        """Запуск синхронизации одного PHC с другим с настраиваемой задержкой
        
        Args:
            source_ptp: Исходное PTP устройство (например, /dev/ptp2)
            target_ptp: Целевое PTP устройство (например, /dev/ptp0)
            offset_ns: Задержка в наносекундах (положительная или отрицательная)
            rate: Скорость коррекции (0.0 = автоматическая)
        """
        try:
            # Валидируем offset
            if not self._validate_offset(offset_ns):
                return False
            
            # Валидируем rate
            if rate < 0.0 or rate > 1.0:
                self.logger.error(f"Скорость коррекции {rate} должна быть в диапазоне 0.0-1.0")
                return False
            
            # Проверяем доступность устройств
            if not os.path.exists(source_ptp) or not os.path.exists(target_ptp):
                self.logger.error(f"PTP устройства недоступны: {source_ptp}, {target_ptp}")
                return False
            
            # Применяем компенсацию через phc_ctl если offset не равен 0
            if offset_ns != 0:
                self.logger.info(f"Применение компенсации {offset_ns} нс через phc_ctl...")
                try:
                    # phc_ctl adj принимает offset в секундах
                    offset_sec = offset_ns / 1_000_000_000.0
                    adj_cmd = ["sudo", "-n", "phc_ctl", target_ptp, "--", "adj", str(offset_sec)]
                    result = subprocess.run(adj_cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        self.logger.info(f"✅ Компенсация {offset_ns} нс применена к {target_ptp}")
                    else:
                        self.logger.warning(f"⚠️ Предупреждение: phc_ctl adj не удался: {result.stderr}")
                        self.logger.info("Продолжаем без предварительной компенсации...")
                        
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                    self.logger.warning(f"⚠️ Предупреждение: phc_ctl adj ошибка: {e}")
                    self.logger.info("Продолжаем без предварительной компенсации...")

            # Строим команду phc2sys как в терминале: phc2sys -c /dev/ptp0 -s /dev/ptp2 -O0 -m
            cmd = ["phc2sys", "-c", target_ptp, "-s", source_ptp]
            
            # Используем параметры как в рабочей команде
            cmd.extend(["-O", "0"])
            
            # Добавляем скорость коррекции если указана
            if rate != 0.0:
                cmd.extend(["-R", str(rate)])
                self.logger.info(f"Скорость коррекции: {rate}")
            else:
                cmd.extend(["-R", "16"])
            
            # Добавляем -m в конце
            cmd.append("-m")
            
            self.logger.info(f"Выполняем команду: {' '.join(cmd)}")
            self.logger.info(f"Отладочная информация: cmd = {cmd}")
            
            # Запускаем в фоне
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.logger.info(f"Запущена синхронизация PHC: {source_ptp} -> {target_ptp}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при запуске синхронизации PHC: {e}")
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
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception):
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
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
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