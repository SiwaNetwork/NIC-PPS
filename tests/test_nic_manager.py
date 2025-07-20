"""
Тесты для NIC менеджера
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Добавляем путь к core модулю
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.nic_manager import IntelNICManager, PPSMode, NICInfo


class TestIntelNICManager(unittest.TestCase):
    """Тесты для IntelNICManager"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.nic_manager = IntelNICManager()
    
    def test_pps_mode_enum(self):
        """Тест перечисления PPSMode"""
        self.assertEqual(PPSMode.DISABLED.value, "disabled")
        self.assertEqual(PPSMode.INPUT.value, "input")
        self.assertEqual(PPSMode.OUTPUT.value, "output")
        self.assertEqual(PPSMode.BOTH.value, "both")
    
    def test_nic_info_dataclass(self):
        """Тест структуры данных NICInfo"""
        nic = NICInfo(
            name="eth0",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.100",
            status="up",
            speed="1000 Mbps",
            duplex="full",
            pps_mode=PPSMode.DISABLED,
            tcxo_enabled=False,
            temperature=45.5
        )
        
        self.assertEqual(nic.name, "eth0")
        self.assertEqual(nic.mac_address, "00:11:22:33:44:55")
        self.assertEqual(nic.ip_address, "192.168.1.100")
        self.assertEqual(nic.status, "up")
        self.assertEqual(nic.speed, "1000 Mbps")
        self.assertEqual(nic.duplex, "full")
        self.assertEqual(nic.pps_mode, PPSMode.DISABLED)
        self.assertFalse(nic.tcxo_enabled)
        self.assertEqual(nic.temperature, 45.5)
    
    @patch('core.nic_manager.netifaces.interfaces')
    @patch('core.nic_manager.netifaces.ifaddresses')
    @patch('os.path.exists')
    @patch('os.path.basename')
    @patch('os.readlink')
    def test_discover_nics(self, mock_readlink, mock_basename, mock_exists, mock_ifaddresses, mock_interfaces):
        """Тест обнаружения NIC карт"""
        # Настройка моков
        mock_interfaces.return_value = ["eth0", "eth1"]
        mock_exists.return_value = True
        mock_basename.return_value = "igb"
        mock_readlink.return_value = "/sys/class/net/eth0/device/driver"
        
        mock_ifaddresses.return_value = {
            netifaces.AF_LINK: [{'addr': '00:11:22:33:44:55'}],
            netifaces.AF_INET: [{'addr': '192.168.1.100'}]
        }
        
        # Выполнение теста
        self.nic_manager._discover_nics()
        
        # Проверки
        self.assertIsInstance(self.nic_manager.nic_list, list)
    
    @patch('os.path.exists')
    @patch('os.path.basename')
    @patch('os.readlink')
    def test_is_intel_nic(self, mock_readlink, mock_basename, mock_exists):
        """Тест проверки Intel NIC карты"""
        mock_exists.return_value = True
        mock_readlink.return_value = "/sys/class/net/eth0/device/driver"
        
        # Тест с поддерживаемым драйвером
        mock_basename.return_value = "igb"
        self.assertTrue(self.nic_manager._is_intel_nic("eth0"))
        
        # Тест с неподдерживаемым драйвером
        mock_basename.return_value = "e1000"
        self.assertFalse(self.nic_manager._is_intel_nic("eth0"))
    
    @patch('builtins.open', new_callable=mock_open, read_data="1000")
    @patch('os.path.exists')
    def test_get_interface_speed(self, mock_exists, mock_file):
        """Тест получения скорости интерфейса"""
        mock_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = "1000"
        
        speed = self.nic_manager._get_interface_speed("eth0")
        self.assertEqual(speed, "1000 Mbps")
    
    @patch('builtins.open', new_callable=mock_open, read_data="full")
    @patch('os.path.exists')
    def test_get_interface_duplex(self, mock_exists, mock_file):
        """Тест получения режима дуплекса"""
        mock_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = "full"
        
        duplex = self.nic_manager._get_interface_duplex("eth0")
        self.assertEqual(duplex, "full")
    
    @patch('os.path.exists')
    def test_get_pps_mode(self, mock_exists):
        """Тест получения режима PPS"""
        # Тест отключенного PPS
        mock_exists.return_value = False
        mode = self.nic_manager._get_pps_mode("eth0")
        self.assertEqual(mode, PPSMode.DISABLED)
        
        # Тест входного PPS
        def mock_exists_side_effect(path):
            return "pps_input" in path
        mock_exists.side_effect = mock_exists_side_effect
        mode = self.nic_manager._get_pps_mode("eth0")
        self.assertEqual(mode, PPSMode.INPUT)
        
        # Тест выходного PPS
        def mock_exists_side_effect(path):
            return "pps_output" in path
        mock_exists.side_effect = mock_exists_side_effect
        mode = self.nic_manager._get_pps_mode("eth0")
        self.assertEqual(mode, PPSMode.OUTPUT)
        
        # Тест обоих режимов
        def mock_exists_side_effect(path):
            return "pps_input" in path or "pps_output" in path
        mock_exists.side_effect = mock_exists_side_effect
        mode = self.nic_manager._get_pps_mode("eth0")
        self.assertEqual(mode, PPSMode.BOTH)
    
    @patch('builtins.open', new_callable=mock_open, read_data="1")
    @patch('os.path.exists')
    def test_is_tcxo_enabled(self, mock_exists, mock_file):
        """Тест проверки включенного TCXO"""
        mock_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = "1"
        
        enabled = self.nic_manager._is_tcxo_enabled("eth0")
        self.assertTrue(enabled)
        
        # Тест отключенного TCXO
        mock_file.return_value.__enter__.return_value.read.return_value = "0"
        enabled = self.nic_manager._is_tcxo_enabled("eth0")
        self.assertFalse(enabled)
    
    @patch('subprocess.run')
    def test_set_pps_mode(self, mock_run):
        """Тест установки режима PPS"""
        # Настройка мока
        mock_run.return_value = MagicMock()
        
        # Тест отключения PPS
        success = self.nic_manager.set_pps_mode("eth0", PPSMode.DISABLED)
        self.assertTrue(success)
        mock_run.assert_called()
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_set_tcxo_enabled(self, mock_exists, mock_file):
        """Тест установки TCXO"""
        mock_exists.return_value = True
        
        # Тест включения TCXO
        success = self.nic_manager.set_tcxo_enabled("eth0", True)
        self.assertTrue(success)
        
        # Тест отключения TCXO
        success = self.nic_manager.set_tcxo_enabled("eth0", False)
        self.assertTrue(success)
    
    @patch('builtins.open', new_callable=mock_open, read_data="45000")
    @patch('os.path.exists')
    def test_get_temperature(self, mock_exists, mock_file):
        """Тест получения температуры"""
        mock_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = "45000"
        
        temp = self.nic_manager.get_temperature("eth0")
        self.assertEqual(temp, 45.0)
    
    @patch('builtins.open', new_callable=mock_open, read_data="eth0: 1000 2000 0 0 3000 4000 0 0")
    def test_get_statistics(self, mock_file):
        """Тест получения статистики"""
        stats = self.nic_manager.get_statistics("eth0")
        
        # Проверяем, что статистика содержит ожидаемые ключи
        expected_keys = ['rx_bytes', 'rx_packets', 'rx_errors', 'rx_dropped',
                        'tx_bytes', 'tx_packets', 'tx_errors', 'tx_dropped']
        for key in expected_keys:
            self.assertIn(key, stats)


class TestPPSMode(unittest.TestCase):
    """Тесты для PPSMode"""
    
    def test_pps_mode_values(self):
        """Тест значений PPSMode"""
        self.assertEqual(PPSMode.DISABLED.value, "disabled")
        self.assertEqual(PPSMode.INPUT.value, "input")
        self.assertEqual(PPSMode.OUTPUT.value, "output")
        self.assertEqual(PPSMode.BOTH.value, "both")
    
    def test_pps_mode_from_value(self):
        """Тест создания PPSMode из значения"""
        self.assertEqual(PPSMode("disabled"), PPSMode.DISABLED)
        self.assertEqual(PPSMode("input"), PPSMode.INPUT)
        self.assertEqual(PPSMode("output"), PPSMode.OUTPUT)
        self.assertEqual(PPSMode("both"), PPSMode.BOTH)


if __name__ == '__main__':
    unittest.main()