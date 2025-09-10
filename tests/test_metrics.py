"""
Тесты для системы мониторинга и метрик
"""

import pytest
import time
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Добавляем путь к проекту
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitoring.metrics import MetricsCollector, HealthChecker


class TestMetricsCollector:
    """Тесты для MetricsCollector"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.collector = MetricsCollector()
    
    def test_init(self):
        """Тест инициализации сборщика метрик"""
        assert self.collector is not None
        assert self.collector.registry is not None
        assert hasattr(self.collector, 'http_requests_total')
        assert hasattr(self.collector, 'pps_signals_total')
        assert hasattr(self.collector, 'system_cpu_usage')
    
    def test_record_http_request(self):
        """Тест записи HTTP запроса"""
        self.collector.record_http_request('GET', '/api/nics', 200, 0.5)
        
        # Проверяем, что метрика была записана
        metrics = self.collector.get_metrics()
        assert 'http_requests_total' in metrics
        assert 'method="GET"' in metrics
        assert 'endpoint="/api/nics"' in metrics
        assert 'status="200"' in metrics
    
    def test_record_pps_signal(self):
        """Тест записи PPS сигнала"""
        self.collector.record_pps_signal('enp3s0', 'input')
        
        metrics = self.collector.get_metrics()
        assert 'pps_signals_total' in metrics
        assert 'interface="enp3s0"' in metrics
        assert 'type="input"' in metrics
    
    def test_record_pps_mode_change(self):
        """Тест записи изменения PPS режима"""
        self.collector.record_pps_mode_change('enp3s0', 'disabled', 'output')
        
        metrics = self.collector.get_metrics()
        assert 'pps_mode_changes_total' in metrics
        assert 'interface="enp3s0"' in metrics
        assert 'from_mode="disabled"' in metrics
        assert 'to_mode="output"' in metrics
    
    def test_record_ptp_error(self):
        """Тест записи PTP ошибки"""
        self.collector.record_ptp_error('enp3s0', 'sync_failed')
        
        metrics = self.collector.get_metrics()
        assert 'ptp_sync_errors_total' in metrics
        assert 'interface="enp3s0"' in metrics
        assert 'error_type="sync_failed"' in metrics
    
    def test_update_ptp_offset(self):
        """Тест обновления PTP offset"""
        self.collector.update_ptp_offset('enp3s0', 123.45)
        
        metrics = self.collector.get_metrics()
        assert 'ptp_offset_nanoseconds' in metrics
        assert 'interface="enp3s0"' in metrics
        assert '123.45' in metrics
    
    def test_update_nic_status(self):
        """Тест обновления статуса NIC"""
        self.collector.update_nic_status('enp3s0', True)
        
        metrics = self.collector.get_metrics()
        assert 'nic_status' in metrics
        assert 'interface="enp3s0"' in metrics
        assert '1.0' in metrics  # True = 1
    
    def test_update_nic_temperature(self):
        """Тест обновления температуры NIC"""
        self.collector.update_nic_temperature('enp3s0', 45.5)
        
        metrics = self.collector.get_metrics()
        assert 'nic_temperature_celsius' in metrics
        assert 'interface="enp3s0"' in metrics
        assert '45.5' in metrics
    
    def test_update_nic_temperature_none(self):
        """Тест обновления температуры NIC с None"""
        # Не должно вызывать ошибку
        self.collector.update_nic_temperature('enp3s0', None)
        
        metrics = self.collector.get_metrics()
        # Температура не должна быть в метриках, если None
        assert 'nic_temperature_celsius' not in metrics or 'enp3s0' not in metrics
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_partitions')
    @patch('psutil.disk_usage')
    def test_update_system_metrics(self, mock_disk_usage, mock_disk_partitions, 
                                 mock_memory, mock_cpu):
        """Тест обновления системных метрик"""
        # Мокаем системные данные
        mock_cpu.return_value = 25.5
        mock_memory.return_value = Mock(percent=60.0)
        mock_disk_partitions.return_value = [
            Mock(device='/dev/sda1', mountpoint='/')
        ]
        mock_disk_usage.return_value = Mock(used=1000000, total=2000000)
        
        # Сбрасываем время последнего обновления
        self.collector.last_system_update = 0
        
        self.collector.update_system_metrics()
        
        metrics = self.collector.get_metrics()
        assert 'system_cpu_usage_percent' in metrics
        assert 'system_memory_usage_percent' in metrics
        assert 'system_disk_usage_percent' in metrics
    
    def test_get_metrics_summary(self):
        """Тест получения сводки метрик"""
        summary = self.collector.get_metrics_summary()
        
        assert 'timestamp' in summary
        assert 'system' in summary
        assert 'metrics_count' in summary
        assert isinstance(summary['timestamp'], (int, float))
        assert isinstance(summary['system'], dict)
        assert isinstance(summary['metrics_count'], int)


class TestHealthChecker:
    """Тесты для HealthChecker"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.checker = HealthChecker()
    
    def test_init(self):
        """Тест инициализации проверки состояния"""
        assert self.checker is not None
        assert hasattr(self.checker, 'checks')
        assert 'system' in self.checker.checks
        assert 'network' in self.checker.checks
        assert 'ptp' in self.checker.checks
        assert 'pps' in self.checker.checks
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_check_system_healthy(self, mock_memory, mock_cpu):
        """Тест проверки системы - здоровое состояние"""
        mock_cpu.return_value = 50.0
        mock_memory.return_value = Mock(percent=60.0)
        
        result = self.checker._check_system()
        
        assert result['status'] == 'healthy'
        assert 'cpu_usage' in result
        assert 'memory_usage' in result
        assert result['cpu_usage'] == 50.0
        assert result['memory_usage'] == 60.0
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_check_system_warning(self, mock_memory, mock_cpu):
        """Тест проверки системы - предупреждение"""
        mock_cpu.return_value = 85.0  # Высокая загрузка CPU
        mock_memory.return_value = Mock(percent=60.0)
        
        result = self.checker._check_system()
        
        assert result['status'] == 'warning'
        assert result['details']['cpu_ok'] is False
        assert result['details']['memory_ok'] is True
    
    @patch('psutil.cpu_percent')
    def test_check_system_error(self, mock_cpu):
        """Тест проверки системы - ошибка"""
        mock_cpu.side_effect = Exception("System error")
        
        result = self.checker._check_system()
        
        assert result['status'] == 'error'
        assert 'error' in result
        assert 'System error' in result['error']
    
    @patch('psutil.net_if_addrs')
    def test_check_network_healthy(self, mock_net_if):
        """Тест проверки сети - здоровое состояние"""
        mock_net_if.return_value = {
            'enp3s0': [Mock(family=Mock(name='AF_INET'), address='192.168.1.100')],
            'lo': [Mock(family=Mock(name='AF_INET'), address='127.0.0.1')]
        }
        
        result = self.checker._check_network()
        
        assert result['status'] == 'healthy'
        assert 'interfaces' in result
        assert 'count' in result
        assert result['count'] >= 1
    
    @patch('psutil.net_if_addrs')
    def test_check_network_warning(self, mock_net_if):
        """Тест проверки сети - предупреждение (нет активных интерфейсов)"""
        mock_net_if.return_value = {
            'lo': [Mock(family=Mock(name='AF_INET'), address='127.0.0.1')]
        }
        
        result = self.checker._check_network()
        
        assert result['status'] == 'warning'
        assert result['count'] == 0
    
    @patch('os.listdir')
    def test_check_ptp_healthy(self, mock_listdir):
        """Тест проверки PTP - здоровое состояние"""
        mock_listdir.return_value = ['ptp0', 'ptp1', 'ptp2', 'other']
        
        result = self.checker._check_ptp()
        
        assert result['status'] == 'healthy'
        assert 'devices' in result
        assert 'count' in result
        assert result['count'] == 3
        assert 'ptp0' in result['devices']
        assert 'ptp1' in result['devices']
        assert 'ptp2' in result['devices']
    
    @patch('os.listdir')
    def test_check_ptp_warning(self, mock_listdir):
        """Тест проверки PTP - предупреждение (нет PTP устройств)"""
        mock_listdir.return_value = ['other', 'files']
        
        result = self.checker._check_ptp()
        
        assert result['status'] == 'warning'
        assert result['count'] == 0
    
    @patch('subprocess.run')
    def test_check_pps_healthy(self, mock_run):
        """Тест проверки PPS - здоровое состояние"""
        mock_run.return_value = Mock(returncode=0, stdout="PTP devices found")
        
        result = self.checker._check_pps()
        
        assert result['status'] == 'healthy'
        assert result['testptp_available'] is True
        assert 'output' in result
    
    @patch('subprocess.run')
    def test_check_pps_error(self, mock_run):
        """Тест проверки PPS - ошибка"""
        mock_run.return_value = Mock(returncode=1, stderr="testptp not found")
        
        result = self.checker._check_pps()
        
        assert result['status'] == 'error'
        assert result['testptp_available'] is False
        assert 'testptp not found' in result['output']
    
    @patch('subprocess.run')
    def test_check_pps_timeout(self, mock_run):
        """Тест проверки PPS - таймаут"""
        mock_run.side_effect = Exception("Timeout")
        
        result = self.checker._check_pps()
        
        assert result['status'] == 'error'
        assert 'error' in result
        assert 'Timeout' in result['error']
    
    def test_run_all_checks(self):
        """Тест запуска всех проверок"""
        with patch.object(self.checker, '_check_system') as mock_system, \
             patch.object(self.checker, '_check_network') as mock_network, \
             patch.object(self.checker, '_check_ptp') as mock_ptp, \
             patch.object(self.checker, '_check_pps') as mock_pps:
            
            mock_system.return_value = {'status': 'healthy'}
            mock_network.return_value = {'status': 'healthy'}
            mock_ptp.return_value = {'status': 'healthy'}
            mock_pps.return_value = {'status': 'healthy'}
            
            result = self.checker.run_all_checks()
            
            assert 'overall_status' in result
            assert 'timestamp' in result
            assert 'checks' in result
            assert result['overall_status'] == 'healthy'
            assert len(result['checks']) == 4
    
    def test_run_all_checks_with_errors(self):
        """Тест запуска всех проверок с ошибками"""
        with patch.object(self.checker, '_check_system') as mock_system, \
             patch.object(self.checker, '_check_network') as mock_network, \
             patch.object(self.checker, '_check_ptp') as mock_ptp, \
             patch.object(self.checker, '_check_pps') as mock_pps:
            
            mock_system.return_value = {'status': 'error', 'error': 'System error'}
            mock_network.return_value = {'status': 'healthy'}
            mock_ptp.return_value = {'status': 'warning'}
            mock_pps.return_value = {'status': 'healthy'}
            
            result = self.checker.run_all_checks()
            
            # Проверяем, что результат содержит все проверки
            assert 'checks' in result
            assert 'system' in result['checks']
            assert 'network' in result['checks']
            assert 'ptp' in result['checks']
            assert 'pps' in result['checks']
            assert result['checks']['network']['status'] == 'healthy'
            assert result['checks']['pps']['status'] == 'healthy'


if __name__ == '__main__':
    pytest.main([__file__])
