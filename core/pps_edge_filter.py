"""
Модуль для фильтрации PPS событий и устранения проблемы с двойными фронтами
Работает на уровне приложения без необходимости патча драйвера
"""

import time
import logging
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import threading
import queue


class PPSEventType(Enum):
    """Типы PPS событий"""
    RISING_EDGE = "rising"
    FALLING_EDGE = "falling"
    UNKNOWN = "unknown"


@dataclass
class PPSEvent:
    """Структура PPS события"""
    timestamp: float
    event_type: PPSEventType
    pin_index: int
    raw_data: str


class PPSEdgeFilter:
    """Фильтр для устранения двойных фронтов PPS"""
    
    def __init__(self, min_interval: float = 0.5, max_interval: float = 1.5):
        """
        Инициализация фильтра
        
        Args:
            min_interval: Минимальный интервал между событиями (сек)
            max_interval: Максимальный интервал между событиями (сек)
        """
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.last_event_time = 0.0
        self.event_history: List[PPSEvent] = []
        self.logger = logging.getLogger(__name__)
        
        # Статистика
        self.total_events = 0
        self.filtered_events = 0
        self.valid_events = 0
        
    def filter_event(self, event: PPSEvent) -> Optional[PPSEvent]:
        """
        Фильтрация PPS события для устранения двойных фронтов
        
        Args:
            event: PPS событие для фильтрации
            
        Returns:
            Отфильтрованное событие или None если событие отфильтровано
        """
        self.total_events += 1
        current_time = event.timestamp
        
        # Проверяем интервал с последним событием
        if self.last_event_time > 0:
            interval = current_time - self.last_event_time
            
            # Если интервал слишком мал - это вероятно двойной фронт
            if interval < self.min_interval:
                self.filtered_events += 1
                self.logger.debug(f"Отфильтровано событие: интервал {interval:.6f} сек < {self.min_interval} сек")
                return None
            
            # Если интервал слишком большой - возможно пропуск события
            if interval > self.max_interval:
                self.logger.warning(f"Большой интервал между событиями: {interval:.6f} сек")
        
        # Событие прошло фильтрацию
        self.last_event_time = current_time
        self.valid_events += 1
        self.event_history.append(event)
        
        # Ограничиваем историю последними 100 событиями
        if len(self.event_history) > 100:
            self.event_history = self.event_history[-100:]
        
        return event
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики фильтрации"""
        return {
            'total_events': self.total_events,
            'filtered_events': self.filtered_events,
            'valid_events': self.valid_events,
            'filter_rate': self.filtered_events / max(1, self.total_events) * 100,
            'last_event_time': self.last_event_time,
            'history_size': len(self.event_history)
        }
    
    def reset_statistics(self):
        """Сброс статистики"""
        self.total_events = 0
        self.filtered_events = 0
        self.valid_events = 0
        self.last_event_time = 0.0
        self.event_history.clear()


class PPSMonitor:
    """Монитор PPS событий с автоматической фильтрацией"""
    
    def __init__(self, ptp_device: str, pin_index: int = 1):
        """
        Инициализация монитора
        
        Args:
            ptp_device: PTP устройство (например, /dev/ptp0)
            pin_index: Индекс пина для мониторинга
        """
        self.ptp_device = ptp_device
        self.pin_index = pin_index
        self.filter = PPSEdgeFilter()
        self.logger = logging.getLogger(__name__)
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.event_queue = queue.Queue()
        
    def start_monitoring(self, callback=None):
        """
        Запуск мониторинга PPS событий
        
        Args:
            callback: Функция обратного вызова для обработки отфильтрованных событий
        """
        if self.monitoring:
            self.logger.warning("Мониторинг уже запущен")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(callback,),
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info(f"Запущен мониторинг PPS событий для {self.ptp_device}")
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        self.logger.info("Мониторинг PPS событий остановлен")
    
    def _monitor_loop(self, callback=None):
        """Основной цикл мониторинга"""
        try:
            while self.monitoring:
                # Читаем события через testptp
                events = self._read_pps_events(count=1, timeout=1)
                
                for raw_event in events:
                    if not self.monitoring:
                        break
                    
                    # Парсим событие
                    parsed_event = self._parse_event(raw_event)
                    if parsed_event:
                        # Фильтруем событие
                        filtered_event = self.filter.filter_event(parsed_event)
                        
                        if filtered_event:
                            # Вызываем callback если он задан
                            if callback:
                                try:
                                    callback(filtered_event)
                                except Exception as e:
                                    self.logger.error(f"Ошибка в callback: {e}")
                            
                            # Добавляем в очередь
                            try:
                                self.event_queue.put_nowait(filtered_event)
                            except queue.Full:
                                # Удаляем старое событие если очередь полная
                                try:
                                    self.event_queue.get_nowait()
                                    self.event_queue.put_nowait(filtered_event)
                                except queue.Empty:
                                    pass
                
        except Exception as e:
            self.logger.error(f"Ошибка в цикле мониторинга: {e}")
        finally:
            self.monitoring = False
    
    def _read_pps_events(self, count: int = 1, timeout: int = 5) -> List[str]:
        """
        Чтение PPS событий через testptp
        
        Args:
            count: Количество событий для чтения
            timeout: Таймаут в секундах
            
        Returns:
            Список строк событий
        """
        try:
            result = subprocess.run(
                ["testptp", "-d", self.ptp_device, "-e", str(count)],
                capture_output=True, text=True, timeout=timeout
            )
            
            if result.returncode == 0:
                events = []
                for line in result.stdout.split('\n'):
                    if 'event' in line and 'index' in line:
                        events.append(line.strip())
                return events
            else:
                self.logger.debug(f"testptp вернул код {result.returncode}: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            # Таймаут - это нормально, просто нет новых событий
            return []
        except Exception as e:
            self.logger.error(f"Ошибка чтения PPS событий: {e}")
            return []
    
    def _parse_event(self, event_line: str) -> Optional[PPSEvent]:
        """
        Парсинг строки события в структуру PPSEvent
        
        Args:
            event_line: Строка события от testptp
            
        Returns:
            Объект PPSEvent или None если парсинг не удался
        """
        try:
            # Пример строки: "event index 1 at 1234567890.123456789"
            parts = event_line.split()
            if len(parts) >= 6:
                pin_index = int(parts[2])
                timestamp = float(parts[4])
                
                # Определяем тип события по интервалу (эвристика)
                event_type = self._determine_event_type(timestamp)
                
                return PPSEvent(
                    timestamp=timestamp,
                    event_type=event_type,
                    pin_index=pin_index,
                    raw_data=event_line
                )
        except (ValueError, IndexError) as e:
            self.logger.debug(f"Ошибка парсинга события '{event_line}': {e}")
        
        return None
    
    def _determine_event_type(self, timestamp: float) -> PPSEventType:
        """
        Определение типа события (эвристический метод)
        
        Args:
            timestamp: Временная метка события
            
        Returns:
            Тип события
        """
        # Простая эвристика: если интервал близок к 1 секунде - восходящий фронт
        if self.filter.last_event_time > 0:
            interval = timestamp - self.filter.last_event_time
            if 0.9 <= interval <= 1.1:
                return PPSEventType.RISING_EDGE
            elif 0.4 <= interval <= 0.6:
                return PPSEventType.FALLING_EDGE
        
        return PPSEventType.UNKNOWN
    
    def get_filtered_events(self, max_events: int = 10) -> List[PPSEvent]:
        """
        Получение отфильтрованных событий из очереди
        
        Args:
            max_events: Максимальное количество событий
            
        Returns:
            Список отфильтрованных событий
        """
        events = []
        for _ in range(max_events):
            try:
                event = self.event_queue.get_nowait()
                events.append(event)
            except queue.Empty:
                break
        return events
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики мониторинга"""
        stats = self.filter.get_statistics()
        stats.update({
            'ptp_device': self.ptp_device,
            'pin_index': self.pin_index,
            'monitoring': self.monitoring,
            'queue_size': self.event_queue.qsize()
        })
        return stats


class PPSManager:
    """Менеджер для управления PPS мониторингом и фильтрацией"""
    
    def __init__(self):
        self.monitors: Dict[str, PPSMonitor] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_monitor(self, ptp_device: str, pin_index: int = 1) -> PPSMonitor:
        """
        Создание монитора PPS для устройства
        
        Args:
            ptp_device: PTP устройство
            pin_index: Индекс пина
            
        Returns:
            Объект PPSMonitor
        """
        monitor = PPSMonitor(ptp_device, pin_index)
        self.monitors[ptp_device] = monitor
        return monitor
    
    def start_monitoring(self, ptp_device: str, callback=None):
        """Запуск мониторинга для устройства"""
        if ptp_device in self.monitors:
            self.monitors[ptp_device].start_monitoring(callback)
        else:
            self.logger.error(f"Монитор для {ptp_device} не найден")
    
    def stop_monitoring(self, ptp_device: str):
        """Остановка мониторинга для устройства"""
        if ptp_device in self.monitors:
            self.monitors[ptp_device].stop_monitoring()
    
    def stop_all_monitoring(self):
        """Остановка всего мониторинга"""
        for monitor in self.monitors.values():
            monitor.stop_monitoring()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики всех мониторов"""
        stats = {}
        for device, monitor in self.monitors.items():
            stats[device] = monitor.get_statistics()
        return stats


# Глобальный экземпляр менеджера
pps_manager = PPSManager()
