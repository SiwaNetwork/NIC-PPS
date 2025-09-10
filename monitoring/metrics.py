"""
Система мониторинга и метрик для SHIWA NIC-PPS
Версия 1.1.0
"""

import time
import psutil
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from flask import request, g
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Сборщик метрик для мониторинга системы"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self._setup_metrics()
        self._setup_system_metrics()
    
    def _setup_metrics(self):
        """Настройка основных метрик"""
        
        # HTTP метрики
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # PPS метрики
        self.pps_signals_total = Counter(
            'pps_signals_total',
            'Total PPS signals received',
            ['interface', 'type'],
            registry=self.registry
        )
        
        self.pps_mode_changes = Counter(
            'pps_mode_changes_total',
            'Total PPS mode changes',
            ['interface', 'from_mode', 'to_mode'],
            registry=self.registry
        )
        
        # PTP метрики
        self.ptp_sync_errors = Counter(
            'ptp_sync_errors_total',
            'Total PTP synchronization errors',
            ['interface', 'error_type'],
            registry=self.registry
        )
        
        self.ptp_offset = Gauge(
            'ptp_offset_nanoseconds',
            'PTP time offset in nanoseconds',
            ['interface'],
            registry=self.registry
        )
        
        # Системные метрики
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            ['device'],
            registry=self.registry
        )
        
        # NIC метрики
        self.nic_status = Gauge(
            'nic_status',
            'NIC interface status (1=up, 0=down)',
            ['interface'],
            registry=self.registry
        )
        
        self.nic_temperature = Gauge(
            'nic_temperature_celsius',
            'NIC temperature in Celsius',
            ['interface'],
            registry=self.registry
        )
        
        # Информационные метрики
        self.app_info = Info(
            'app_info',
            'Application information',
            registry=self.registry
        )
        
        # Устанавливаем информацию о приложении
        self.app_info.info({
            'version': '1.1.0',
            'build_date': '2025-09-09',
            'description': 'SHIWA NIC-PPS Configuration and Monitoring Tool'
        })
    
    def _setup_system_metrics(self):
        """Настройка системных метрик"""
        self.last_system_update = 0
        self.system_update_interval = 30  # секунд
    
    def update_system_metrics(self):
        """Обновление системных метрик"""
        current_time = time.time()
        if current_time - self.last_system_update < self.system_update_interval:
            return
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.percent)
            
            # Disk usage
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    usage_percent = (usage.used / usage.total) * 100
                    self.system_disk_usage.labels(device=partition.device).set(usage_percent)
                except PermissionError:
                    continue
            
            self.last_system_update = current_time
            
        except Exception as e:
            logger.error(f"Ошибка обновления системных метрик: {e}")
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Запись HTTP запроса"""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status_code
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_pps_signal(self, interface: str, signal_type: str):
        """Запись PPS сигнала"""
        self.pps_signals_total.labels(
            interface=interface,
            type=signal_type
        ).inc()
    
    def record_pps_mode_change(self, interface: str, from_mode: str, to_mode: str):
        """Запись изменения PPS режима"""
        self.pps_mode_changes.labels(
            interface=interface,
            from_mode=from_mode,
            to_mode=to_mode
        ).inc()
    
    def record_ptp_error(self, interface: str, error_type: str):
        """Запись PTP ошибки"""
        self.ptp_sync_errors.labels(
            interface=interface,
            error_type=error_type
        ).inc()
    
    def update_ptp_offset(self, interface: str, offset_ns: float):
        """Обновление PTP offset"""
        self.ptp_offset.labels(interface=interface).set(offset_ns)
    
    def update_nic_status(self, interface: str, status: bool):
        """Обновление статуса NIC"""
        self.nic_status.labels(interface=interface).set(1 if status else 0)
    
    def update_nic_temperature(self, interface: str, temperature: Optional[float]):
        """Обновление температуры NIC"""
        if temperature is not None:
            self.nic_temperature.labels(interface=interface).set(temperature)
    
    def get_metrics(self) -> str:
        """Получение метрик в формате Prometheus"""
        self.update_system_metrics()
        return generate_latest(self.registry).decode('utf-8')
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Получение сводки метрик"""
        return {
            'timestamp': time.time(),
            'system': {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': {
                    partition.device: psutil.disk_usage(partition.mountpoint).percent
                    for partition in psutil.disk_partitions()
                    if not partition.device.startswith('/dev/loop')
                }
            },
            'metrics_count': len(list(self.registry.collect()))
        }


# Глобальный экземпляр сборщика метрик
metrics_collector = MetricsCollector()


def init_flask_metrics(app):
    """Инициализация метрик для Flask приложения"""
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            metrics_collector.record_http_request(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status_code=response.status_code,
                duration=duration
            )
        return response
    
    @app.route('/metrics')
    def metrics():
        """Endpoint для Prometheus метрик"""
        return metrics_collector.get_metrics(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    @app.route('/api/metrics/summary')
    def metrics_summary():
        """API для получения сводки метрик"""
        return metrics_collector.get_metrics_summary()


class HealthChecker:
    """Проверка состояния системы"""
    
    def __init__(self):
        self.checks = {
            'system': self._check_system,
            'network': self._check_network,
            'ptp': self._check_ptp,
            'pps': self._check_pps
        }
    
    def _check_system(self) -> Dict[str, Any]:
        """Проверка системных ресурсов"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            return {
                'status': 'healthy' if cpu_percent < 80 and memory.percent < 80 else 'warning',
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'details': {
                    'cpu_ok': cpu_percent < 80,
                    'memory_ok': memory.percent < 80
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _check_network(self) -> Dict[str, Any]:
        """Проверка сетевых интерфейсов"""
        try:
            interfaces = psutil.net_if_addrs()
            active_interfaces = []
            
            for interface, addresses in interfaces.items():
                if interface.startswith('en') or interface.startswith('eth'):
                    active_interfaces.append({
                        'name': interface,
                        'addresses': [addr.address for addr in addresses if addr.family.name == 'AF_INET']
                    })
            
            return {
                'status': 'healthy' if active_interfaces else 'warning',
                'interfaces': active_interfaces,
                'count': len(active_interfaces)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _check_ptp(self) -> Dict[str, Any]:
        """Проверка PTP устройств"""
        try:
            import os
            ptp_devices = [f for f in os.listdir('/dev') if f.startswith('ptp')]
            
            return {
                'status': 'healthy' if ptp_devices else 'warning',
                'devices': ptp_devices,
                'count': len(ptp_devices)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _check_pps(self) -> Dict[str, Any]:
        """Проверка PPS функциональности"""
        try:
            import subprocess
            result = subprocess.run(['testptp', '-l'], capture_output=True, text=True, timeout=5)
            
            return {
                'status': 'healthy' if result.returncode == 0 else 'error',
                'testptp_available': result.returncode == 0,
                'output': result.stdout if result.returncode == 0 else result.stderr
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Запуск всех проверок"""
        results = {}
        overall_status = 'healthy'
        
        for check_name, check_func in self.checks.items():
            try:
                result = check_func()
                results[check_name] = result
                
                if result['status'] == 'error':
                    overall_status = 'error'
                elif result['status'] == 'warning' and overall_status == 'healthy':
                    overall_status = 'warning'
                    
            except Exception as e:
                results[check_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                overall_status = 'error'
        
        return {
            'overall_status': overall_status,
            'timestamp': time.time(),
            'checks': results
        }


# Глобальный экземпляр проверки состояния
health_checker = HealthChecker()
