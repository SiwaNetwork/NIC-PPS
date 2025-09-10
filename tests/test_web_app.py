"""
Тесты для веб-приложения
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Добавляем путь к проекту
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from web.app import app
from core.nic_manager import PPSMode


class TestWebApp:
    """Тесты для веб-приложения"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.app = app.test_client()
        self.app.testing = True
    
    def test_index_page(self):
        """Тест главной страницы"""
        response = self.app.get('/')
        assert response.status_code == 200
        assert b'SHIWA NIC-PPS' in response.data
    
    def test_version_api(self):
        """Тест API версии"""
        response = self.app.get('/api/version')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'version' in data
        assert 'build_date' in data
        assert 'description' in data
    
    @patch('web.app.nic_manager')
    def test_nics_api(self, mock_nic_manager):
        """Тест API списка NIC"""
        # Мокаем данные NIC
        mock_nic = Mock()
        mock_nic.name = 'enp3s0'
        mock_nic.mac_address = 'a0:37:9f:a5:04:0d'
        mock_nic.status = 'up'
        mock_nic.pps_mode = PPSMode.OUTPUT
        
        mock_nic_manager.get_all_nics.return_value = [mock_nic]
        
        response = self.app.get('/api/nics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True
        assert 'nics' in data
        assert len(data['nics']) == 1
        assert data['nics'][0]['name'] == 'enp3s0'
    
    @patch('web.app.nic_manager')
    def test_nic_info_api(self, mock_nic_manager):
        """Тест API информации о NIC"""
        # Мокаем информацию о NIC
        mock_nic = Mock()
        mock_nic.name = 'enp3s0'
        mock_nic.mac_address = 'a0:37:9f:a5:04:0d'
        mock_nic.status = 'up'
        mock_nic.pps_mode = PPSMode.OUTPUT
        mock_nic.speed = '1000Mb/s'
        mock_nic.duplex = 'Full'
        
        mock_nic_manager.get_nic_info.return_value = mock_nic
        
        response = self.app.get('/api/nics/enp3s0')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True
        assert 'nic' in data
        assert data['nic']['name'] == 'enp3s0'
    
    @patch('web.app.nic_manager')
    def test_set_pps_mode_success(self, mock_nic_manager):
        """Тест успешной установки PPS режима"""
        mock_nic_manager.set_pps_mode.return_value = True
        
        # Мокаем текущий режим
        mock_current_nic = Mock()
        mock_current_nic.pps_mode = PPSMode.DISABLED
        mock_nic_manager.get_nic_info.return_value = mock_current_nic
        
        response = self.app.post('/api/nics/enp3s0/pps', 
                               data=json.dumps({'mode': 'output'}),
                               content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True
        
        # Проверяем, что был вызван set_pps_mode
        mock_nic_manager.set_pps_mode.assert_called_once_with('enp3s0', PPSMode.OUTPUT)
    
    @patch('web.app.nic_manager')
    def test_set_pps_mode_invalid_mode(self, mock_nic_manager):
        """Тест установки неверного PPS режима"""
        response = self.app.post('/api/nics/enp3s0/pps', 
                               data=json.dumps({'mode': 'invalid'}),
                               content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is False
        assert 'error' in data
        assert 'Неверный режим PPS' in data['error']
    
    @patch('web.app.nic_manager')
    def test_set_pps_mode_failure(self, mock_nic_manager):
        """Тест неудачной установки PPS режима"""
        mock_nic_manager.set_pps_mode.return_value = False
        
        # Мокаем текущий режим
        mock_current_nic = Mock()
        mock_current_nic.pps_mode = PPSMode.DISABLED
        mock_nic_manager.get_nic_info.return_value = mock_current_nic
        
        response = self.app.post('/api/nics/enp3s0/pps', 
                               data=json.dumps({'mode': 'output'}),
                               content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is False
    
    @patch('web.app.timenic_manager')
    def test_timenics_api(self, mock_timenic_manager):
        """Тест API списка TimeNIC"""
        # Мокаем данные TimeNIC
        mock_timenic = Mock()
        mock_timenic.name = 'enp3s0'
        mock_timenic.mac_address = 'a0:37:9f:a5:04:0d'
        mock_timenic.ptp_device = '/dev/ptp0'
        
        mock_timenic_manager.get_all_timenics.return_value = [mock_timenic]
        
        response = self.app.get('/api/timenics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True
        assert 'timenics' in data
        assert len(data['timenics']) == 1
        assert data['timenics'][0]['name'] == 'enp3s0'
    
    def test_ptp_devices_api(self):
        """Тест API PTP устройств"""
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = ['/dev/ptp0', '/dev/ptp1', '/dev/ptp2']
            
            response = self.app.get('/api/ptp/devices')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'success' in data
            assert data['success'] is True
            assert 'devices' in data
            assert len(data['devices']) == 3
    
    def test_health_check_api(self):
        """Тест API проверки состояния"""
        response = self.app.get('/api/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'overall_status' in data
        assert 'timestamp' in data
        assert 'checks' in data
    
    def test_metrics_endpoint(self):
        """Тест endpoint метрик"""
        response = self.app.get('/metrics')
        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'
    
    def test_metrics_summary_api(self):
        """Тест API сводки метрик"""
        response = self.app.get('/api/metrics/summary')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'timestamp' in data
        assert 'system' in data
        assert 'metrics_count' in data
    
    @patch('web.app.nic_manager')
    def test_monitoring_start(self, mock_nic_manager):
        """Тест запуска мониторинга"""
        mock_nic_manager.get_statistics.return_value = {'rx_packets': 1000}
        mock_nic_manager.get_ptp_statistics.return_value = {'offset': 123}
        
        response = self.app.post('/api/monitoring/start',
                               data=json.dumps({'interface': 'enp3s0'}),
                               content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True
    
    def test_monitoring_start_no_interface(self):
        """Тест запуска мониторинга без интерфейса"""
        response = self.app.post('/api/monitoring/start',
                               data=json.dumps({}),
                               content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is False
        assert 'error' in data
    
    def test_monitoring_stop(self):
        """Тест остановки мониторинга"""
        response = self.app.post('/api/monitoring/stop')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True


if __name__ == '__main__':
    pytest.main([__file__])
