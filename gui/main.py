"""
Главное окно GUI приложения для конфигурации и мониторинга Intel NIC
"""

import sys
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QPushButton,
    QComboBox, QLabel, QGroupBox, QGridLayout, QTextEdit,
    QProgressBar, QCheckBox, QSpinBox, QDoubleSpinBox,
    QMessageBox, QSplitter, QFrame
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QPalette, QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# Добавляем путь к core модулю
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.nic_manager import IntelNICManager, PPSMode, NICInfo
from core.timenic_manager import TimeNICManager, TimeNICInfo, PTPInfo, PTMStatus


class MonitoringThread(QThread):
    """Поток для мониторинга в фоновом режиме"""
    data_updated = pyqtSignal(dict)
    timenic_data_updated = pyqtSignal(dict)
    
    def __init__(self, nic_manager: IntelNICManager, timenic_manager: TimeNICManager = None):
        super().__init__()
        self.nic_manager = nic_manager
        self.timenic_manager = timenic_manager
        self.running = True
    
    def run(self):
        while self.running:
            try:
                # Обновляем данные обычных NIC каждую секунду
                data = {}
                for nic in self.nic_manager.get_all_nics():
                    stats = self.nic_manager.get_statistics(nic.name)
                    temp = self.nic_manager.get_temperature(nic.name)
                    data[nic.name] = {
                        'stats': stats,
                        'temperature': temp,
                        'status': nic.status
                    }
                self.data_updated.emit(data)
                
                # Обновляем данные TimeNIC каждую секунду
                if self.timenic_manager:
                    timenic_data = {}
                    for timenic in self.timenic_manager.get_all_timenics():
                        stats = self.timenic_manager.get_statistics(timenic.name)
                        timenic_data[timenic.name] = {
                            'stats': stats,
                            'temperature': timenic.temperature,
                            'status': timenic.status,
                            'pps_mode': timenic.pps_mode.value,
                            'tcxo_enabled': timenic.tcxo_enabled,
                            'ptm_status': timenic.ptm_status.value,
                            'sma1_status': timenic.sma1_status,
                            'sma2_status': timenic.sma2_status,
                            'phc_offset': timenic.phc_offset,
                            'phc_frequency': timenic.phc_frequency
                        }
                    self.timenic_data_updated.emit(timenic_data)
                
                self.msleep(1000)  # 1 секунда
            except Exception as e:
                print(f"Ошибка в потоке мониторинга: {e}")
    
    def stop(self):
        self.running = False


class NICTableWidget(QTableWidget):
    """Виджет таблицы для отображения NIC карт"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса таблицы"""
        headers = [
            "Имя", "MAC адрес", "IP адрес", "Статус", 
            "Скорость", "Дуплекс", "PPS режим", "TCXO", "Температура"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Настройка внешнего вида
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Автоматическое изменение размера столбцов
        self.resizeColumnsToContents()
    
    def update_data(self, nics: list[NICInfo]):
        """Обновление данных в таблице"""
        self.setRowCount(len(nics))
        
        for row, nic in enumerate(nics):
            self.setItem(row, 0, QTableWidgetItem(nic.name))
            self.setItem(row, 1, QTableWidgetItem(nic.mac_address))
            self.setItem(row, 2, QTableWidgetItem(nic.ip_address))
            
            # Статус с цветовой индикацией
            status_item = QTableWidgetItem(nic.status)
            if nic.status == "up":
                status_item.setBackground(QColor(144, 238, 144))  # Светло-зеленый
            else:
                status_item.setBackground(QColor(255, 182, 193))  # Светло-красный
            self.setItem(row, 3, status_item)
            
            self.setItem(row, 4, QTableWidgetItem(nic.speed))
            self.setItem(row, 5, QTableWidgetItem(nic.duplex))
            self.setItem(row, 6, QTableWidgetItem(nic.pps_mode.value))
            
            # TCXO с цветовой индикацией
            tcxo_item = QTableWidgetItem("✓" if nic.tcxo_enabled else "✗")
            if nic.tcxo_enabled:
                tcxo_item.setBackground(QColor(144, 238, 144))  # Светло-зеленый
            else:
                tcxo_item.setBackground(QColor(255, 182, 193))  # Светло-красный
            self.setItem(row, 7, tcxo_item)
            
            # Температура
            temp_text = f"{nic.temperature:.1f}°C" if nic.temperature else "N/A"
            self.setItem(row, 8, QTableWidgetItem(temp_text))
        
        self.resizeColumnsToContents()


class TimeNICTableWidget(QTableWidget):
    """Виджет таблицы для отображения TimeNIC карт"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса таблицы"""
        headers = [
            "Имя", "MAC адрес", "IP адрес", "Статус", 
            "PPS режим", "TCXO", "PTM", "SMA1", "SMA2", "PHC Offset", "Температура"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Настройка внешнего вида
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Автоматическое изменение размера столбцов
        self.resizeColumnsToContents()
    
    def update_data(self, timenics: list[TimeNICInfo]):
        """Обновление данных в таблице"""
        self.setRowCount(len(timenics))
        
        for row, timenic in enumerate(timenics):
            self.setItem(row, 0, QTableWidgetItem(timenic.name))
            self.setItem(row, 1, QTableWidgetItem(timenic.mac_address))
            self.setItem(row, 2, QTableWidgetItem(timenic.ip_address))
            
            # Статус с цветовой индикацией
            status_item = QTableWidgetItem(timenic.status)
            if timenic.status == "up":
                status_item.setBackground(QColor(144, 238, 144))  # Светло-зеленый
            else:
                status_item.setBackground(QColor(255, 182, 193))  # Светло-красный
            self.setItem(row, 3, status_item)
            
            self.setItem(row, 4, QTableWidgetItem(timenic.pps_mode.value))
            
            # TCXO с цветовой индикацией
            tcxo_item = QTableWidgetItem("✓" if timenic.tcxo_enabled else "✗")
            if timenic.tcxo_enabled:
                tcxo_item.setBackground(QColor(144, 238, 144))  # Светло-зеленый
            else:
                tcxo_item.setBackground(QColor(255, 182, 193))  # Светло-красный
            self.setItem(row, 5, tcxo_item)
            
            # PTM статус
            ptm_item = QTableWidgetItem(timenic.ptm_status.value)
            if timenic.ptm_status.value == "enabled":
                ptm_item.setBackground(QColor(144, 238, 144))  # Светло-зеленый
            elif timenic.ptm_status.value == "disabled":
                ptm_item.setBackground(QColor(255, 182, 193))  # Светло-красный
            else:
                ptm_item.setBackground(QColor(255, 255, 224))  # Светло-желтый
            self.setItem(row, 6, ptm_item)
            
            # SMA статусы
            sma1_item = QTableWidgetItem(timenic.sma1_status)
            if timenic.sma1_status == "enabled":
                sma1_item.setBackground(QColor(144, 238, 144))  # Светло-зеленый
            else:
                sma1_item.setBackground(QColor(255, 182, 193))  # Светло-красный
            self.setItem(row, 7, sma1_item)
            
            sma2_item = QTableWidgetItem(timenic.sma2_status)
            if timenic.sma2_status == "enabled":
                sma2_item.setBackground(QColor(144, 238, 144))  # Светло-зеленый
            else:
                sma2_item.setBackground(QColor(255, 182, 193))  # Светло-красный
            self.setItem(row, 8, sma2_item)
            
            # PHC Offset
            phc_offset_text = str(timenic.phc_offset) if timenic.phc_offset else "N/A"
            self.setItem(row, 9, QTableWidgetItem(phc_offset_text))
            
            # Температура
            temp_text = f"{timenic.temperature:.1f}°C" if timenic.temperature else "N/A"
            self.setItem(row, 10, QTableWidgetItem(temp_text))
        
        self.resizeColumnsToContents()


class ConfigurationWidget(QWidget):
    """Виджет для конфигурации NIC карт"""
    
    def __init__(self, nic_manager: IntelNICManager):
        super().__init__()
        self.nic_manager = nic_manager
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса конфигурации"""
        layout = QVBoxLayout()
        
        # Выбор NIC карты
        nic_group = QGroupBox("Выбор сетевой карты")
        nic_layout = QHBoxLayout()
        
        self.nic_combo = QComboBox()
        self.nic_combo.currentTextChanged.connect(self.on_nic_selected)
        nic_layout.addWidget(QLabel("NIC карта:"))
        nic_layout.addWidget(self.nic_combo)
        nic_layout.addStretch()
        
        nic_group.setLayout(nic_layout)
        layout.addWidget(nic_group)
        
        # Настройки PPS
        pps_group = QGroupBox("Настройки PPS")
        pps_layout = QGridLayout()
        
        self.pps_combo = QComboBox()
        self.pps_combo.addItems([mode.value for mode in PPSMode])
        pps_layout.addWidget(QLabel("PPS режим:"), 0, 0)
        pps_layout.addWidget(self.pps_combo, 0, 1)
        
        self.apply_pps_btn = QPushButton("Применить PPS")
        self.apply_pps_btn.clicked.connect(self.apply_pps_settings)
        pps_layout.addWidget(self.apply_pps_btn, 0, 2)
        
        pps_group.setLayout(pps_layout)
        layout.addWidget(pps_group)
        
        # Настройки TCXO
        tcxo_group = QGroupBox("Настройки TCXO")
        tcxo_layout = QHBoxLayout()
        
        self.tcxo_checkbox = QCheckBox("Включить TCXO")
        tcxo_layout.addWidget(self.tcxo_checkbox)
        
        self.apply_tcxo_btn = QPushButton("Применить TCXO")
        self.apply_tcxo_btn.clicked.connect(self.apply_tcxo_settings)
        tcxo_layout.addWidget(self.apply_tcxo_btn)
        tcxo_layout.addStretch()
        
        tcxo_group.setLayout(tcxo_layout)
        layout.addWidget(tcxo_group)
        
        # Информация о выбранной карте
        info_group = QGroupBox("Информация о карте")
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(150)
        self.info_text.setReadOnly(True)
        info_group.setLayout(QVBoxLayout())
        info_group.layout().addWidget(self.info_text)
        layout.addWidget(info_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Обновляем список NIC карт
        self.update_nic_list()
    
    def update_nic_list(self):
        """Обновление списка NIC карт"""
        self.nic_combo.clear()
        nics = self.nic_manager.get_all_nics()
        for nic in nics:
            self.nic_combo.addItem(nic.name)
    
    def on_nic_selected(self, nic_name: str):
        """Обработчик выбора NIC карты"""
        if not nic_name:
            return
        
        nic = self.nic_manager.get_nic_by_name(nic_name)
        if nic:
            # Устанавливаем текущие значения
            self.pps_combo.setCurrentText(nic.pps_mode.value)
            self.tcxo_checkbox.setChecked(nic.tcxo_enabled)
            
            # Показываем информацию о карте
            info_text = f"""
Имя: {nic.name}
MAC адрес: {nic.mac_address}
IP адрес: {nic.ip_address}
Статус: {nic.status}
Скорость: {nic.speed}
Дуплекс: {nic.duplex}
PPS режим: {nic.pps_mode.value}
TCXO: {'Включен' if nic.tcxo_enabled else 'Отключен'}
Температура: {f'{nic.temperature:.1f}°C' if nic.temperature else 'N/A'}
            """
            self.info_text.setText(info_text.strip())
    
    def apply_pps_settings(self):
        """Применение настроек PPS"""
        nic_name = self.nic_combo.currentText()
        if not nic_name:
            QMessageBox.warning(self, "Ошибка", "Выберите NIC карту")
            return
        
        mode = PPSMode(self.pps_combo.currentText())
        success = self.nic_manager.set_pps_mode(nic_name, mode)
        
        if success:
            QMessageBox.information(self, "Успех", f"PPS режим изменен на {mode.value}")
            # Обновляем список и текущее отображение
            self.update_nic_list()
            # Обновляем отображение выбранной карты
            self.on_nic_selected(nic_name)
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось изменить PPS режим")
    
    def apply_tcxo_settings(self):
        """Применение настроек TCXO"""
        nic_name = self.nic_combo.currentText()
        if not nic_name:
            QMessageBox.warning(self, "Ошибка", "Выберите NIC карту")
            return
        
        enabled = self.tcxo_checkbox.isChecked()
        success = self.nic_manager.set_tcxo_enabled(nic_name, enabled)
        
        if success:
            QMessageBox.information(self, "Успех", f"TCXO {'включен' if enabled else 'отключен'}")
            # Обновляем список и текущее отображение
            self.update_nic_list()
            # Обновляем отображение выбранной карты
            self.on_nic_selected(nic_name)
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось изменить настройки TCXO")


class TimeNICConfigurationWidget(QWidget):
    """Виджет для конфигурации TimeNIC карт"""
    
    def __init__(self, timenic_manager: TimeNICManager):
        super().__init__()
        self.timenic_manager = timenic_manager
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout()
        
        # Группа для выбора TimeNIC
        timenic_group = QGroupBox("Выбор TimeNIC карты")
        timenic_layout = QVBoxLayout()
        
        self.timenic_combo = QComboBox()
        self.timenic_combo.currentTextChanged.connect(self.on_timenic_selected)
        timenic_layout.addWidget(QLabel("TimeNIC карта:"))
        timenic_layout.addWidget(self.timenic_combo)
        
        timenic_group.setLayout(timenic_layout)
        layout.addWidget(timenic_group)
        
        # Группа для PPS настроек
        pps_group = QGroupBox("Настройки PPS (SMA разъемы)")
        pps_layout = QGridLayout()
        
        self.pps_combo = QComboBox()
        self.pps_combo.addItems(["disabled", "input", "output", "both"])
        pps_layout.addWidget(QLabel("PPS режим:"), 0, 0)
        pps_layout.addWidget(self.pps_combo, 0, 1)
        
        # SMA информация
        self.sma1_label = QLabel("SMA1 (SDP0) - выход PPS: N/A")
        self.sma2_label = QLabel("SMA2 (SDP1) - вход PPS: N/A")
        pps_layout.addWidget(self.sma1_label, 1, 0, 1, 2)
        pps_layout.addWidget(self.sma2_label, 2, 0, 1, 2)
        
        self.apply_pps_btn = QPushButton("Применить PPS")
        self.apply_pps_btn.clicked.connect(self.apply_pps_settings)
        pps_layout.addWidget(self.apply_pps_btn, 3, 0, 1, 2)
        
        pps_group.setLayout(pps_layout)
        layout.addWidget(pps_group)
        
        # Группа для TCXO и PTM настроек
        advanced_group = QGroupBox("Расширенные настройки")
        advanced_layout = QGridLayout()
        
        self.tcxo_checkbox = QCheckBox("Включить TCXO")
        advanced_layout.addWidget(self.tcxo_checkbox, 0, 0)
        
        self.ptm_checkbox = QCheckBox("Включить PTM")
        advanced_layout.addWidget(self.ptm_checkbox, 0, 1)
        
        self.apply_advanced_btn = QPushButton("Применить настройки")
        self.apply_advanced_btn.clicked.connect(self.apply_advanced_settings)
        advanced_layout.addWidget(self.apply_advanced_btn, 1, 0, 1, 2)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # Группа для PHC синхронизации
        phc_group = QGroupBox("PHC синхронизация")
        phc_layout = QGridLayout()
        
        self.phc_offset_label = QLabel("PHC Offset: N/A")
        self.phc_frequency_label = QLabel("PHC Frequency: N/A")
        phc_layout.addWidget(self.phc_offset_label, 0, 0)
        phc_layout.addWidget(self.phc_frequency_label, 0, 1)
        
        self.start_phc_btn = QPushButton("Запустить синхронизацию PHC")
        self.start_phc_btn.clicked.connect(self.start_phc_sync)
        phc_layout.addWidget(self.start_phc_btn, 1, 0, 1, 2)
        
        phc_group.setLayout(phc_layout)
        layout.addWidget(phc_group)
        
        self.setLayout(layout)
        self.update_timenic_list()
    
    def update_timenic_list(self):
        """Обновление списка TimeNIC карт"""
        self.timenic_combo.clear()
        timenics = self.timenic_manager.get_all_timenics()
        for timenic in timenics:
            self.timenic_combo.addItem(timenic.name)
    
    def on_timenic_selected(self, timenic_name: str):
        """Обработка выбора TimeNIC карты"""
        if not timenic_name:
            return
        
        timenic = self.timenic_manager.get_timenic_by_name(timenic_name)
        if timenic:
            # Устанавливаем текущие значения
            index = self.pps_combo.findText(timenic.pps_mode.value)
            if index >= 0:
                self.pps_combo.setCurrentIndex(index)
            
            self.tcxo_checkbox.setChecked(timenic.tcxo_enabled)
            self.ptm_checkbox.setChecked(timenic.ptm_status.value == "enabled")
            
            # Обновляем SMA информацию
            self.sma1_label.setText(f"SMA1 (SDP0) - выход PPS: {timenic.sma1_status}")
            self.sma2_label.setText(f"SMA2 (SDP1) - вход PPS: {timenic.sma2_status}")
            
            # Обновляем PHC информацию
            phc_offset_text = str(timenic.phc_offset) if timenic.phc_offset else "N/A"
            phc_frequency_text = str(timenic.phc_frequency) if timenic.phc_frequency else "N/A"
            self.phc_offset_label.setText(f"PHC Offset: {phc_offset_text}")
            self.phc_frequency_label.setText(f"PHC Frequency: {phc_frequency_text}")
    
    def apply_pps_settings(self):
        """Применение PPS настроек"""
        timenic_name = self.timenic_combo.currentText()
        if not timenic_name:
            return
        
        from core.timenic_manager import PPSMode
        pps_mode = PPSMode(self.pps_combo.currentText())
        
        try:
            success = self.timenic_manager.set_pps_mode(timenic_name, pps_mode)
            if success:
                QMessageBox.information(self, "Успех", f"PPS режим {pps_mode.value} установлен для {timenic_name}")
                # Обновляем список и текущее отображение
                self.update_timenic_list()
                self.on_timenic_selected(timenic_name)
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось установить PPS режим для {timenic_name}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при установке PPS: {e}")
    
    def apply_advanced_settings(self):
        """Применение расширенных настроек"""
        timenic_name = self.timenic_combo.currentText()
        if not timenic_name:
            return
        
        tcxo_enabled = self.tcxo_checkbox.isChecked()
        ptm_enabled = self.ptm_checkbox.isChecked()
        
        try:
            # Применяем TCXO
            tcxo_success = self.timenic_manager.set_tcxo_enabled(timenic_name, tcxo_enabled)
            
            # Применяем PTM
            ptm_success = True
            if ptm_enabled:
                ptm_success = self.timenic_manager.enable_ptm(timenic_name)
            
            if tcxo_success and ptm_success:
                QMessageBox.information(self, "Успех", f"Настройки применены для {timenic_name}")
                # Обновляем список и текущее отображение
                self.update_timenic_list()
                self.on_timenic_selected(timenic_name)
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось применить все настройки для {timenic_name}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при применении настроек: {e}")
    
    def start_phc_sync(self):
        """Запуск синхронизации PHC"""
        timenic_name = self.timenic_combo.currentText()
        if not timenic_name:
            return
        
        try:
            success = self.timenic_manager.start_phc_synchronization(timenic_name)
            if success:
                QMessageBox.information(self, "Успех", f"Синхронизация PHC запущена для {timenic_name}")
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось запустить синхронизацию PHC для {timenic_name}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при запуске синхронизации PHC: {e}")


class MonitoringWidget(QWidget):
    """Виджет для мониторинга производительности"""
    
    def __init__(self, nic_manager: IntelNICManager, timenic_manager: TimeNICManager = None):
        super().__init__()
        self.nic_manager = nic_manager
        self.timenic_manager = timenic_manager
        self.monitoring_data = {}
        self.timenic_monitoring_data = {}
        
        # Инициализация данных для графиков TimeNIC
        self.timenic_traffic_data = {'rx': [], 'tx': [], 'time': []}
        self.timenic_temp_data = {'temp': [], 'time': []}
        
        self.setup_ui()
        
        # Запускаем поток мониторинга
        self.monitoring_thread = MonitoringThread(nic_manager, timenic_manager)
        self.monitoring_thread.data_updated.connect(self.update_monitoring_data)
        self.monitoring_thread.timenic_data_updated.connect(self.update_timenic_monitoring_data)
        self.monitoring_thread.start()
    
    def setup_ui(self):
        """Настройка интерфейса мониторинга"""
        layout = QVBoxLayout()
        
        # Выбор NIC для мониторинга
        monitor_group = QGroupBox("Мониторинг")
        monitor_layout = QHBoxLayout()
        
        self.monitor_nic_combo = QComboBox()
        self.monitor_nic_combo.currentTextChanged.connect(self.on_monitor_nic_selected)
        monitor_layout.addWidget(QLabel("NIC карта:"))
        monitor_layout.addWidget(self.monitor_nic_combo)
        monitor_layout.addStretch()
        
        monitor_group.setLayout(monitor_layout)
        layout.addWidget(monitor_group)
        
        # Добавляем выбор TimeNIC для мониторинга
        if self.timenic_manager:
            timenic_monitor_group = QGroupBox("Мониторинг TimeNIC")
            timenic_monitor_layout = QHBoxLayout()
            
            self.monitor_timenic_combo = QComboBox()
            self.monitor_timenic_combo.currentTextChanged.connect(self.on_monitor_timenic_selected)
            timenic_monitor_layout.addWidget(QLabel("TimeNIC карта:"))
            timenic_monitor_layout.addWidget(self.monitor_timenic_combo)
            timenic_monitor_layout.addStretch()
            
            timenic_monitor_group.setLayout(timenic_monitor_layout)
            layout.addWidget(timenic_monitor_group)
        
        # Графики
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # График трафика
        traffic_group = QGroupBox("Общий трафик")
        self.traffic_canvas = self.create_traffic_chart()
        traffic_group.setLayout(QVBoxLayout())
        traffic_group.layout().addWidget(self.traffic_canvas)
        splitter.addWidget(traffic_group)
        
        # График PTP трафика
        ptp_traffic_group = QGroupBox("PTP трафик")
        self.ptp_traffic_canvas = self.create_ptp_traffic_chart()
        ptp_traffic_group.setLayout(QVBoxLayout())
        ptp_traffic_group.layout().addWidget(self.ptp_traffic_canvas)
        splitter.addWidget(ptp_traffic_group)
        
        # График температуры
        temp_group = QGroupBox("Температура")
        self.temp_canvas = self.create_temperature_chart()
        temp_group.setLayout(QVBoxLayout())
        temp_group.layout().addWidget(self.temp_canvas)
        splitter.addWidget(temp_group)
        
        layout.addWidget(splitter)
        
        # Графики для TimeNIC
        if self.timenic_manager:
            timenic_splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # График трафика TimeNIC
            timenic_traffic_group = QGroupBox("Трафик TimeNIC")
            self.timenic_traffic_canvas = self.create_timenic_traffic_chart()
            timenic_traffic_group.setLayout(QVBoxLayout())
            timenic_traffic_group.layout().addWidget(self.timenic_traffic_canvas)
            timenic_splitter.addWidget(timenic_traffic_group)
            
            # График температуры TimeNIC
            timenic_temp_group = QGroupBox("Температура TimeNIC")
            self.timenic_temp_canvas = self.create_timenic_temperature_chart()
            timenic_temp_group.setLayout(QVBoxLayout())
            timenic_temp_group.layout().addWidget(self.timenic_temp_canvas)
            timenic_splitter.addWidget(timenic_temp_group)
            
            layout.addWidget(timenic_splitter)
        
        # Статистика
        stats_group = QGroupBox("Статистика")
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(100)
        self.stats_text.setReadOnly(True)
        stats_group.setLayout(QVBoxLayout())
        stats_group.layout().addWidget(self.stats_text)
        layout.addWidget(stats_group)
        
        # Добавляем статистику TimeNIC
        if self.timenic_manager:
            timenic_stats_group = QGroupBox("Статистика TimeNIC")
            self.timenic_stats_text = QTextEdit()
            self.timenic_stats_text.setMaximumHeight(150)
            self.timenic_stats_text.setReadOnly(True)
            timenic_stats_group.setLayout(QVBoxLayout())
            timenic_stats_group.layout().addWidget(self.timenic_stats_text)
            layout.addWidget(timenic_stats_group)
        
        self.setLayout(layout)
        
        # Обновляем список NIC карт
        self.update_monitor_nic_list()
        
        # Обновляем список TimeNIC карт
        if self.timenic_manager:
            self.update_monitor_timenic_list()
    
    def create_traffic_chart(self):
        """Создание графика трафика"""
        fig = Figure(figsize=(6, 4))
        canvas = FigureCanvas(fig)
        self.traffic_ax = fig.add_subplot(111)
        self.traffic_ax.set_title("Трафик (байт/с)")
        self.traffic_ax.set_xlabel("Время")
        self.traffic_ax.set_ylabel("Байт/с")
        self.traffic_data = {'rx': [], 'tx': [], 'time': []}
        return canvas
    
    def create_temperature_chart(self):
        """Создание графика температуры"""
        fig = Figure(figsize=(6, 4))
        canvas = FigureCanvas(fig)
        self.temp_ax = fig.add_subplot(111)
        self.temp_ax.set_title("Температура (°C)")
        self.temp_ax.set_xlabel("Время")
        self.temp_ax.set_ylabel("°C")
        self.temp_data = {'temp': [], 'time': []}
        return canvas
    
    def create_timenic_traffic_chart(self):
        """Создание графика трафика для TimeNIC"""
        fig = Figure(figsize=(6, 4))
        canvas = FigureCanvas(fig)
        self.timenic_traffic_ax = fig.add_subplot(111)
        self.timenic_traffic_ax.set_title("Трафик (байт/с)")
        self.timenic_traffic_ax.set_xlabel("Время")
        self.timenic_traffic_ax.set_ylabel("Байт/с")
        self.timenic_traffic_data = {'rx': [], 'tx': [], 'time': []}
        return canvas
    
    def create_timenic_temperature_chart(self):
        """Создание графика температуры для TimeNIC"""
        fig = Figure(figsize=(6, 4))
        canvas = FigureCanvas(fig)
        self.timenic_temp_ax = fig.add_subplot(111)
        self.timenic_temp_ax.set_title("Температура (°C)")
        self.timenic_temp_ax.set_xlabel("Время")
        self.timenic_temp_ax.set_ylabel("°C")
        self.timenic_temp_data = {'temp': [], 'time': []}
        return canvas
    
    def create_ptp_traffic_chart(self):
        """Создание графика PTP трафика"""
        fig = Figure(figsize=(6, 4))
        canvas = FigureCanvas(fig)
        self.ptp_traffic_ax = fig.add_subplot(111)
        self.ptp_traffic_ax.set_title("PTP трафик (пакеты/с)")
        self.ptp_traffic_ax.set_xlabel("Время")
        self.ptp_traffic_ax.set_ylabel("Пакеты/с")
        self.ptp_traffic_data = {'rx': [], 'tx': [], 'sync': [], 'time': []}
        return canvas
    
    def update_monitor_nic_list(self):
        """Обновление списка NIC карт для мониторинга"""
        self.monitor_nic_combo.clear()
        nics = self.nic_manager.get_all_nics()
        for nic in nics:
            self.monitor_nic_combo.addItem(nic.name)
    
    def update_monitor_timenic_list(self):
        """Обновление списка TimeNIC карт для мониторинга"""
        if self.timenic_manager:
            self.monitor_timenic_combo.clear()
            timenics = self.timenic_manager.get_all_timenics()
            for timenic in timenics:
                self.monitor_timenic_combo.addItem(timenic.name)
    
    def on_monitor_nic_selected(self, nic_name: str):
        """Обработчик выбора NIC для мониторинга"""
        if nic_name:
            # Очищаем данные при смене карты
            self.traffic_data = {'rx': [], 'tx': [], 'time': []}
            self.temp_data = {'temp': [], 'time': []}
            self.update_charts()
    
    def on_monitor_timenic_selected(self, timenic_name: str):
        """Обработчик выбора TimeNIC для мониторинга"""
        if timenic_name:
            # Очищаем данные при смене карты
            self.timenic_monitoring_data = {} # Clear TimeNIC data
            self.update_timenic_charts()
    
    def update_monitoring_data(self, data: dict):
        """Обновление данных мониторинга"""
        self.monitoring_data = data
        self.update_charts()
        self.update_stats()
    
    def update_timenic_monitoring_data(self, data: dict):
        """Обновление данных мониторинга TimeNIC"""
        self.timenic_monitoring_data = data
        self.update_timenic_charts()
        self.update_timenic_stats()
    
    def update_charts(self):
        """Обновление графиков"""
        current_nic = self.monitor_nic_combo.currentText()
        if not current_nic or current_nic not in self.monitoring_data:
            return
        
        data = self.monitoring_data[current_nic]
        current_time = len(self.traffic_data['time'])
        
        # Обновляем данные трафика
        if 'stats' in data:
            stats = data['stats']
            if 'rx_bytes' in stats and 'tx_bytes' in stats:
                if self.traffic_data['time']:
                    # Вычисляем скорость
                    prev_rx = self.traffic_data['rx'][-1] if self.traffic_data['rx'] else 0
                    prev_tx = self.traffic_data['tx'][-1] if self.traffic_data['tx'] else 0
                    rx_speed = stats['rx_bytes'] - prev_rx
                    tx_speed = stats['tx_bytes'] - prev_tx
                else:
                    rx_speed = tx_speed = 0
                
                self.traffic_data['rx'].append(rx_speed)
                self.traffic_data['tx'].append(tx_speed)
                self.traffic_data['time'].append(current_time)
            
            # Обновляем данные PTP трафика
            if 'ptp_rx_packets' in stats and 'ptp_tx_packets' in stats:
                if self.ptp_traffic_data['time']:
                    # Вычисляем скорость PTP пакетов
                    prev_ptp_rx = self.ptp_traffic_data['rx'][-1] if self.ptp_traffic_data['rx'] else 0
                    prev_ptp_tx = self.ptp_traffic_data['tx'][-1] if self.ptp_traffic_data['tx'] else 0
                    prev_ptp_sync = self.ptp_traffic_data['sync'][-1] if self.ptp_traffic_data['sync'] else 0
                    
                    ptp_rx_speed = stats['ptp_rx_packets'] - prev_ptp_rx
                    ptp_tx_speed = stats['ptp_tx_packets'] - prev_ptp_tx
                    ptp_sync_speed = stats.get('ptp_sync_packets', 0) - prev_ptp_sync
                else:
                    ptp_rx_speed = ptp_tx_speed = ptp_sync_speed = 0
                
                self.ptp_traffic_data['rx'].append(ptp_rx_speed)
                self.ptp_traffic_data['tx'].append(ptp_tx_speed)
                self.ptp_traffic_data['sync'].append(ptp_sync_speed)
                self.ptp_traffic_data['time'].append(current_time)
        
        # Обновляем данные температуры
        if 'temperature' in data and data['temperature']:
            self.temp_data['temp'].append(data['temperature'])
            self.temp_data['time'].append(current_time)
        
        # Ограничиваем количество точек на графике
        max_points = 60
        if len(self.traffic_data['time']) > max_points:
            self.traffic_data['rx'] = self.traffic_data['rx'][-max_points:]
            self.traffic_data['tx'] = self.traffic_data['tx'][-max_points:]
            self.traffic_data['time'] = self.traffic_data['time'][-max_points:]
        
        if len(self.ptp_traffic_data['time']) > max_points:
            self.ptp_traffic_data['rx'] = self.ptp_traffic_data['rx'][-max_points:]
            self.ptp_traffic_data['tx'] = self.ptp_traffic_data['tx'][-max_points:]
            self.ptp_traffic_data['sync'] = self.ptp_traffic_data['sync'][-max_points:]
            self.ptp_traffic_data['time'] = self.ptp_traffic_data['time'][-max_points:]
        
        if len(self.temp_data['time']) > max_points:
            self.temp_data['temp'] = self.temp_data['temp'][-max_points:]
            self.temp_data['time'] = self.temp_data['time'][-max_points:]
        
        # Обновляем графики
        self.traffic_ax.clear()
        if self.traffic_data['time']:
            self.traffic_ax.plot(self.traffic_data['time'], self.traffic_data['rx'], label='RX', color='blue')
            self.traffic_ax.plot(self.traffic_data['time'], self.traffic_data['tx'], label='TX', color='red')
            self.traffic_ax.legend()
            self.traffic_ax.set_title("Трафик (байт/с)")
            self.traffic_ax.set_xlabel("Время")
            self.traffic_ax.set_ylabel("Байт/с")
        
        self.temp_ax.clear()
        if self.temp_data['time']:
            self.temp_ax.plot(self.temp_data['time'], self.temp_data['temp'], color='orange')
            self.temp_ax.set_title("Температура (°C)")
            self.temp_ax.set_xlabel("Время")
            self.temp_ax.set_ylabel("°C")
        
        # Обновляем PTP график
        self.ptp_traffic_ax.clear()
        has_data = False
        
        if self.ptp_traffic_data['time']:
            if any(self.ptp_traffic_data['rx']):
                self.ptp_traffic_ax.plot(self.ptp_traffic_data['time'], self.ptp_traffic_data['rx'], label='PTP RX', color='green')
                has_data = True
            if any(self.ptp_traffic_data['tx']):
                self.ptp_traffic_ax.plot(self.ptp_traffic_data['time'], self.ptp_traffic_data['tx'], label='PTP TX', color='purple')
                has_data = True
            if any(self.ptp_traffic_data['sync']):
                self.ptp_traffic_ax.plot(self.ptp_traffic_data['time'], self.ptp_traffic_data['sync'], label='PTP Sync', color='red')
                has_data = True
            
            if has_data:
                self.ptp_traffic_ax.legend()
            
            self.ptp_traffic_ax.set_title("PTP трафик (пакеты/с)")
            self.ptp_traffic_ax.set_xlabel("Время")
            self.ptp_traffic_ax.set_ylabel("Пакеты/с")
        else:
            self.ptp_traffic_ax.text(0.5, 0.5, 'PTP трафик не обнаружен', 
                                    ha='center', va='center', transform=self.ptp_traffic_ax.transAxes)
            self.ptp_traffic_ax.set_title("PTP трафик (пакеты/с)")
        
        self.traffic_canvas.draw()
        self.ptp_traffic_canvas.draw()
        self.temp_canvas.draw()
    
    def update_timenic_charts(self):
        """Обновление графиков TimeNIC"""
        if not self.timenic_manager:
            return

        current_timenic = self.monitor_timenic_combo.currentText()
        if not current_timenic or current_timenic not in self.timenic_monitoring_data:
            return

        data = self.timenic_monitoring_data[current_timenic]
        current_time = len(self.timenic_traffic_data['time'])

        # Обновляем данные трафика
        if 'stats' in data:
            stats = data['stats']
            if 'rx_bytes' in stats and 'tx_bytes' in stats:
                if self.timenic_traffic_data['time']:
                    prev_rx = self.timenic_traffic_data['rx'][-1] if self.timenic_traffic_data['rx'] else 0
                    prev_tx = self.timenic_traffic_data['tx'][-1] if self.timenic_traffic_data['tx'] else 0
                    rx_speed = stats['rx_bytes'] - prev_rx
                    tx_speed = stats['tx_bytes'] - prev_tx
                else:
                    rx_speed = tx_speed = 0
                
                self.timenic_traffic_data['rx'].append(rx_speed)
                self.timenic_traffic_data['tx'].append(tx_speed)
                self.timenic_traffic_data['time'].append(current_time)
        
        # Обновляем данные температуры
        if 'temperature' in data and data['temperature']:
            self.timenic_temp_data['temp'].append(data['temperature'])
            self.timenic_temp_data['time'].append(current_time)
        
        # Ограничиваем количество точек на графике
        max_points = 60
        if len(self.timenic_traffic_data['time']) > max_points:
            self.timenic_traffic_data['rx'] = self.timenic_traffic_data['rx'][-max_points:]
            self.timenic_traffic_data['tx'] = self.timenic_traffic_data['tx'][-max_points:]
            self.timenic_traffic_data['time'] = self.timenic_traffic_data['time'][-max_points:]
        
        if len(self.timenic_temp_data['time']) > max_points:
            self.timenic_temp_data['temp'] = self.timenic_temp_data['temp'][-max_points:]
            self.timenic_temp_data['time'] = self.timenic_temp_data['time'][-max_points:]
        
        # Обновляем графики
        self.timenic_traffic_ax.clear()
        if self.timenic_traffic_data['time']:
            self.timenic_traffic_ax.plot(self.timenic_traffic_data['time'], self.timenic_traffic_data['rx'], label='RX', color='blue')
            self.timenic_traffic_ax.plot(self.timenic_traffic_data['time'], self.timenic_traffic_data['tx'], label='TX', color='red')
            self.timenic_traffic_ax.legend()
            self.timenic_traffic_ax.set_title("Трафик (байт/с)")
            self.timenic_traffic_ax.set_xlabel("Время")
            self.timenic_traffic_ax.set_ylabel("Байт/с")
        
        self.timenic_temp_ax.clear()
        if self.timenic_temp_data['time']:
            self.timenic_temp_ax.plot(self.timenic_temp_data['time'], self.timenic_temp_data['temp'], color='orange')
            self.timenic_temp_ax.set_title("Температура (°C)")
            self.timenic_temp_ax.set_xlabel("Время")
            self.timenic_temp_ax.set_ylabel("°C")
        
        self.timenic_traffic_canvas.draw()
        self.timenic_temp_canvas.draw()
    
    def update_stats(self):
        """Обновление статистики"""
        current_nic = self.monitor_nic_combo.currentText()
        if not current_nic or current_nic not in self.monitoring_data:
            return
        
        data = self.monitoring_data[current_nic]
        stats_text = ""
        
        if 'stats' in data:
            stats = data['stats']
            
            # Основная статистика
            stats_text += f"=== Основная статистика ===\n"
            stats_text += f"Принято пакетов: {stats.get('rx_packets', 0):,}\n"
            stats_text += f"Отправлено пакетов: {stats.get('tx_packets', 0):,}\n"
            stats_text += f"Принято байт: {stats.get('rx_bytes', 0):,}\n"
            stats_text += f"Отправлено байт: {stats.get('tx_bytes', 0):,}\n"
            stats_text += f"Ошибки приема: {stats.get('rx_errors', 0):,}\n"
            stats_text += f"Ошибки отправки: {stats.get('tx_errors', 0):,}\n"
            stats_text += f"Отброшено при приеме: {stats.get('rx_dropped', 0):,}\n"
            stats_text += f"Отброшено при отправке: {stats.get('tx_dropped', 0):,}\n"
            
            # PTP статистика
            ptp_rx_packets = stats.get('ptp_rx_packets', 0)
            ptp_tx_packets = stats.get('ptp_tx_packets', 0)
            ptp_sync_packets = stats.get('ptp_sync_packets', 0)
            ptp_delay_req_packets = stats.get('ptp_delay_req_packets', 0)
            ptp_follow_up_packets = stats.get('ptp_follow_up_packets', 0)
            ptp_delay_resp_packets = stats.get('ptp_delay_resp_packets', 0)
            
            if ptp_rx_packets > 0 or ptp_tx_packets > 0:
                stats_text += f"\n=== PTP статистика ===\n"
                stats_text += f"PTP RX пакетов: {ptp_rx_packets:,}\n"
                stats_text += f"PTP TX пакетов: {ptp_tx_packets:,}\n"
                stats_text += f"Sync пакетов: {ptp_sync_packets:,}\n"
                stats_text += f"Delay Request пакетов: {ptp_delay_req_packets:,}\n"
                stats_text += f"Follow Up пакетов: {ptp_follow_up_packets:,}\n"
                stats_text += f"Delay Response пакетов: {ptp_delay_resp_packets:,}\n"
            else:
                stats_text += f"\n=== PTP статистика ===\n"
                stats_text += f"PTP трафик не обнаружен\n"
        
        if 'temperature' in data and data['temperature']:
            stats_text += f"\nТемпература: {data['temperature']:.1f}°C\n"
        
        if 'status' in data:
            stats_text += f"\nСтатус: {data['status']}"
        
        self.stats_text.setText(stats_text)
    
    def update_timenic_stats(self):
        """Обновление статистики TimeNIC"""
        if not self.timenic_monitoring_data:
            return
        
        current_timenic = self.monitor_timenic_combo.currentText()
        if not current_timenic or current_timenic not in self.timenic_monitoring_data:
            return
        
        data = self.timenic_monitoring_data[current_timenic]
        stats = data.get('stats', {})
        
        self.timenic_stats_text.clear()
        self.timenic_stats_text.append(f"=== Статистика {current_timenic} ===")
        self.timenic_stats_text.append("")
        
        # Основная информация
        self.timenic_stats_text.append(f"Статус: {data.get('status', 'N/A')}")
        self.timenic_stats_text.append(f"PPS режим: {data.get('pps_mode', 'N/A')}")
        self.timenic_stats_text.append(f"TCXO: {'Включен' if data.get('tcxo_enabled') else 'Выключен'}")
        self.timenic_stats_text.append(f"PTM: {data.get('ptm_status', 'N/A')}")
        self.timenic_stats_text.append(f"SMA1: {data.get('sma1_status', 'N/A')}")
        self.timenic_stats_text.append(f"SMA2: {data.get('sma2_status', 'N/A')}")
        self.timenic_stats_text.append(f"PHC Offset: {data.get('phc_offset', 'N/A')}")
        self.timenic_stats_text.append(f"PHC Frequency: {data.get('phc_frequency', 'N/A')}")
        self.timenic_stats_text.append("")
        
        # Статистика трафика
        if stats:
            rx_bytes = stats.get('rx_bytes', 0)
            tx_bytes = stats.get('tx_bytes', 0)
            rx_packets = stats.get('rx_packets', 0)
            tx_packets = stats.get('tx_packets', 0)
            
            self.timenic_stats_text.append("=== Трафик ===")
            self.timenic_stats_text.append(f"Принято байт: {rx_bytes:,}")
            self.timenic_stats_text.append(f"Отправлено байт: {tx_bytes:,}")
            self.timenic_stats_text.append(f"Принято пакетов: {rx_packets:,}")
            self.timenic_stats_text.append(f"Отправлено пакетов: {tx_packets:,}")
        
        # Температура
        temp = data.get('temperature')
        if temp:
            self.timenic_stats_text.append("")
            self.timenic_stats_text.append(f"Температура: {temp:.1f}°C")
        
        self.timenic_stats_text.append("")
        self.timenic_stats_text.append("---")
        self.timenic_stats_text.append("")
    
    def closeEvent(self, event):
        """Обработчик закрытия виджета"""
        if hasattr(self, 'monitoring_thread'):
            self.monitoring_thread.stop()
            self.monitoring_thread.wait()
        super().closeEvent(event)


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.nic_manager = IntelNICManager()
        self.timenic_manager = TimeNICManager()
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса главного окна"""
        self.setWindowTitle("Intel NIC PPS Configuration and Monitoring Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Создаем вкладки
        tab_widget = QTabWidget()
        
        # Вкладка с таблицей NIC карт
        self.nic_table = NICTableWidget()
        tab_widget.addTab(self.nic_table, "NIC карты")
        
        # Вкладка с таблицей TimeNIC карт
        self.timenic_table = TimeNICTableWidget()
        tab_widget.addTab(self.timenic_table, "TimeNIC карты")
        
        # Вкладка конфигурации
        self.config_widget = ConfigurationWidget(self.nic_manager)
        tab_widget.addTab(self.config_widget, "Конфигурация")
        
        # Вкладка конфигурации TimeNIC
        self.timenic_config_widget = TimeNICConfigurationWidget(self.timenic_manager)
        tab_widget.addTab(self.timenic_config_widget, "Конфигурация TimeNIC")
        
        # Вкладка мониторинга
        self.monitor_widget = MonitoringWidget(self.nic_manager, self.timenic_manager)
        tab_widget.addTab(self.monitor_widget, "Мониторинг")
        
        # Основной layout
        layout = QVBoxLayout()
        layout.addWidget(tab_widget)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        central_widget.setLayout(layout)
        
        # Таймер для обновления данных
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_data)
        self.update_timer.start(5000)  # Обновление каждые 5 секунд
        
        # Первоначальное обновление
        self.refresh_data()
    
    def refresh_data(self):
        """Обновление данных"""
        # Обновляем обычные NIC карты
        nics = self.nic_manager.get_all_nics()
        self.nic_table.update_data(nics)
        self.config_widget.update_nic_list()
        self.monitor_widget.update_monitor_nic_list()
        
        # Обновляем TimeNIC карты
        self.timenic_manager.refresh()  # Обновляем список устройств
        timenics = self.timenic_manager.get_all_timenics()
        self.timenic_table.update_data(timenics)
        self.timenic_config_widget.update_timenic_list()


def main():
    """Главная функция"""
    app = QApplication(sys.argv)
    
    # Настройка стиля
    app.setStyle('Fusion')
    
    # Создание и отображение главного окна
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()