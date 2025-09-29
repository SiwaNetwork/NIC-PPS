"""
Главное окно GUI приложения для конфигурации и мониторинга Intel NIC
Современный интерфейс с улучшенным дизайном и функциональностью
"""

import sys
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QPushButton,
    QComboBox, QLabel, QGroupBox, QGridLayout, QTextEdit,
    QProgressBar, QCheckBox, QSpinBox, QDoubleSpinBox,
    QMessageBox, QSplitter, QFrame, QScrollArea, QStackedWidget,
    QStatusBar, QMenuBar, QMenu, QToolBar, QSlider, QDial,
    QLCDNumber, QLineEdit, QFormLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon, QPixmap, QPainter, QLinearGradient, QBrush
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# Добавляем путь к core модулю
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.nic_manager import IntelNICManager, PPSMode, NICInfo
from core.timenic_manager import TimeNICManager, TimeNICInfo, PTPInfo, PTMStatus


class ModernButton(QPushButton):
    """Современная кнопка с градиентным фоном и анимацией"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(35)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5CBF60, stop:1 #4CAF50);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3E8E41, stop:1 #2E7D32);
            }
            QPushButton:disabled {
                background: #cccccc;
                color: #666666;
            }
        """)


class DangerButton(QPushButton):
    """Кнопка для опасных действий (красная)"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(35)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f44336, stop:1 #d32f2f);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff5722, stop:1 #f44336);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d32f2f, stop:1 #b71c1c);
            }
        """)


class ModernGroupBox(QGroupBox):
    """Современная группа с улучшенным стилем"""
    
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: #f8f9fa;
            }
        """)


class StatusIndicator(QLabel):
    """Индикатор статуса с цветовой кодировкой"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setStyleSheet("""
            QLabel {
                border-radius: 10px;
                background-color: #95a5a6;
            }
        """)
    
    def set_status(self, status: str):
        """Установка статуса с соответствующим цветом"""
        if status == "up" or status == "enabled":
            self.setStyleSheet("""
                QLabel {
                    border-radius: 10px;
                    background-color: #27ae60;
                }
            """)
        elif status == "down" or status == "disabled":
            self.setStyleSheet("""
                QLabel {
                    border-radius: 10px;
                    background-color: #e74c3c;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    border-radius: 10px;
                    background-color: #f39c12;
                }
            """)


class ModernProgressBar(QProgressBar):
    """Современный прогресс-бар"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 6px;
            }
        """)


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
                    data[nic.name] = {
                        'stats': stats,
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
    """Современная таблица для отображения NIC карт"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса таблицы"""
        headers = [
            "Статус", "Имя", "MAC адрес", "IP адрес", 
            "Скорость", "Дуплекс", "PPS режим", "TCXO"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Современный стиль таблицы
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #bdc3c7;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #3498db;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                color: #2c3e50;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #ecf0f1;
                color: #2c3e50;
                background-color: white;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34495e, stop:1 #2c3e50);
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        
        # Настройка внешнего вида
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(True)
        
        # Установка минимальной высоты строк (более компактно)
        self.verticalHeader().setDefaultSectionSize(30)
        
        # Автоматическое изменение размера столбцов
        self.resizeColumnsToContents()
    
    def update_data(self, nics: list[NICInfo]):
        """Обновление данных в таблице"""
        self.setRowCount(len(nics))
        
        for row, nic in enumerate(nics):
            # Статус с индикатором
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(5, 5, 5, 5)
            
            status_indicator = StatusIndicator()
            status_indicator.set_status(nic.status)
            status_layout.addWidget(status_indicator)
            
            status_label = QLabel(nic.status.upper())
            status_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            status_layout.addWidget(status_label)
            status_layout.addStretch()
            
            self.setCellWidget(row, 0, status_widget)
            
            # Остальные данные
            self.setItem(row, 1, QTableWidgetItem(nic.name))
            self.setItem(row, 2, QTableWidgetItem(nic.mac_address))
            self.setItem(row, 3, QTableWidgetItem(nic.ip_address))
            self.setItem(row, 4, QTableWidgetItem(nic.speed))
            self.setItem(row, 5, QTableWidgetItem(nic.duplex))
            self.setItem(row, 6, QTableWidgetItem(nic.pps_mode.value))
            
            # TCXO с индикатором
            tcxo_widget = QWidget()
            tcxo_layout = QHBoxLayout(tcxo_widget)
            tcxo_layout.setContentsMargins(5, 5, 5, 5)
            
            tcxo_indicator = StatusIndicator()
            tcxo_indicator.set_status("enabled" if nic.tcxo_enabled else "disabled")
            tcxo_layout.addWidget(tcxo_indicator)
            
            tcxo_label = QLabel("✓" if nic.tcxo_enabled else "✗")
            tcxo_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            tcxo_layout.addWidget(tcxo_label)
            tcxo_layout.addStretch()
            
            self.setCellWidget(row, 7, tcxo_widget)
        
        self.resizeColumnsToContents()


class TimeNICTableWidget(QTableWidget):
    """Современная таблица для отображения TimeNIC карт"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса таблицы"""
        headers = [
            "Статус", "Имя", "MAC адрес", "IP адрес", 
            "PPS режим", "TCXO", "PTM", "SMA1", "SMA2", "PHC Offset"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Современный стиль таблицы
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #bdc3c7;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #3498db;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                color: #2c3e50;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #ecf0f1;
                color: #2c3e50;
                background-color: white;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8e44ad, stop:1 #9b59b6);
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        
        # Настройка внешнего вида
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(True)
        
        # Установка минимальной высоты строк (более компактно)
        self.verticalHeader().setDefaultSectionSize(30)
        
        # Автоматическое изменение размера столбцов
        self.resizeColumnsToContents()
    
    def update_data(self, timenics: list[TimeNICInfo]):
        """Обновление данных в таблице"""
        self.setRowCount(len(timenics))
        
        for row, timenic in enumerate(timenics):
            # Статус с индикатором
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(5, 5, 5, 5)
            
            status_indicator = StatusIndicator()
            status_indicator.set_status(timenic.status)
            status_layout.addWidget(status_indicator)
            
            status_label = QLabel(timenic.status.upper())
            status_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            status_layout.addWidget(status_label)
            status_layout.addStretch()
            
            self.setCellWidget(row, 0, status_widget)
            
            # Остальные данные
            self.setItem(row, 1, QTableWidgetItem(timenic.name))
            self.setItem(row, 2, QTableWidgetItem(timenic.mac_address))
            self.setItem(row, 3, QTableWidgetItem(timenic.ip_address))
            self.setItem(row, 4, QTableWidgetItem(timenic.pps_mode.value))
            
            # TCXO с индикатором
            tcxo_widget = QWidget()
            tcxo_layout = QHBoxLayout(tcxo_widget)
            tcxo_layout.setContentsMargins(5, 5, 5, 5)
            
            tcxo_indicator = StatusIndicator()
            tcxo_indicator.set_status("enabled" if timenic.tcxo_enabled else "disabled")
            tcxo_layout.addWidget(tcxo_indicator)
            
            tcxo_label = QLabel("✓" if timenic.tcxo_enabled else "✗")
            tcxo_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            tcxo_layout.addWidget(tcxo_label)
            tcxo_layout.addStretch()
            
            self.setCellWidget(row, 5, tcxo_widget)
            
            # PTM статус с индикатором
            ptm_widget = QWidget()
            ptm_layout = QHBoxLayout(ptm_widget)
            ptm_layout.setContentsMargins(5, 5, 5, 5)
            
            ptm_indicator = StatusIndicator()
            ptm_indicator.set_status(timenic.ptm_status.value)
            ptm_layout.addWidget(ptm_indicator)
            
            ptm_label = QLabel(timenic.ptm_status.value.upper())
            ptm_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            ptm_layout.addWidget(ptm_label)
            ptm_layout.addStretch()
            
            self.setCellWidget(row, 6, ptm_widget)
            
            # SMA1 статус с индикатором
            sma1_widget = QWidget()
            sma1_layout = QHBoxLayout(sma1_widget)
            sma1_layout.setContentsMargins(5, 5, 5, 5)
            
            sma1_indicator = StatusIndicator()
            sma1_indicator.set_status(timenic.sma1_status)
            sma1_layout.addWidget(sma1_indicator)
            
            sma1_label = QLabel(timenic.sma1_status.upper())
            sma1_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            sma1_layout.addWidget(sma1_label)
            sma1_layout.addStretch()
            
            self.setCellWidget(row, 7, sma1_widget)
            
            # SMA2 статус с индикатором
            sma2_widget = QWidget()
            sma2_layout = QHBoxLayout(sma2_widget)
            sma2_layout.setContentsMargins(5, 5, 5, 5)
            
            sma2_indicator = StatusIndicator()
            sma2_indicator.set_status(timenic.sma2_status)
            sma2_layout.addWidget(sma2_indicator)
            
            sma2_label = QLabel(timenic.sma2_status.upper())
            sma2_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            sma2_layout.addWidget(sma2_label)
            sma2_layout.addStretch()
            
            self.setCellWidget(row, 8, sma2_widget)
            
            # PHC Offset
            phc_offset_text = str(timenic.phc_offset) if timenic.phc_offset else "N/A"
            self.setItem(row, 9, QTableWidgetItem(phc_offset_text))
        
        self.resizeColumnsToContents()


class ConfigurationWidget(QWidget):
    """Современный виджет для конфигурации NIC карт"""
    
    def __init__(self, nic_manager: IntelNICManager):
        super().__init__()
        self.nic_manager = nic_manager
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса конфигурации"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title_label = QLabel("Конфигурация сетевых карт")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title_label)
        
        # Выбор NIC карты
        nic_group = ModernGroupBox("Выбор сетевой карты")
        nic_layout = QFormLayout()
        nic_layout.setSpacing(15)
        
        self.nic_combo = QComboBox()
        self.nic_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #7f8c8d;
                margin-right: 10px;
            }
        """)
        self.nic_combo.currentTextChanged.connect(self.on_nic_selected)
        nic_layout.addRow("NIC карта:", self.nic_combo)
        
        nic_group.setLayout(nic_layout)
        layout.addWidget(nic_group)
        
        # Настройки PPS
        pps_group = ModernGroupBox("Настройки PPS")
        pps_layout = QFormLayout()
        pps_layout.setSpacing(15)
        
        self.pps_combo = QComboBox()
        self.pps_combo.addItems([mode.value for mode in PPSMode])
        self.pps_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #7f8c8d;
                margin-right: 10px;
            }
        """)
        pps_layout.addRow("PPS режим:", self.pps_combo)
        
        self.apply_pps_btn = ModernButton("Применить PPS")
        self.apply_pps_btn.clicked.connect(self.apply_pps_settings)
        pps_layout.addRow("", self.apply_pps_btn)
        
        pps_group.setLayout(pps_layout)
        layout.addWidget(pps_group)
        
        # Настройки TCXO
        tcxo_group = ModernGroupBox("Настройки TCXO")
        tcxo_layout = QFormLayout()
        tcxo_layout.setSpacing(15)
        
        self.tcxo_checkbox = QCheckBox("Включить TCXO")
        self.tcxo_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #2c3e50;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #27ae60;
                border-color: #27ae60;
            }
            QCheckBox::indicator:checked::after {
                content: "✓";
                color: white;
                font-weight: bold;
            }
        """)
        tcxo_layout.addRow("", self.tcxo_checkbox)
        
        self.apply_tcxo_btn = ModernButton("Применить TCXO")
        self.apply_tcxo_btn.clicked.connect(self.apply_tcxo_settings)
        tcxo_layout.addRow("", self.apply_tcxo_btn)
        
        tcxo_group.setLayout(tcxo_layout)
        layout.addWidget(tcxo_group)
        
        # Синхронизация PHC
        sync_group = ModernGroupBox("Синхронизация PHC")
        sync_layout = QGridLayout()
        sync_layout.setSpacing(15)
        
        # PHC2SYS синхронизация
        sync_layout.addWidget(QLabel("Источник PHC:"), 0, 0)
        self.source_ptp_combo = QComboBox()
        self.source_ptp_combo.addItems(["/dev/ptp0", "/dev/ptp1", "/dev/ptp2"])
        self.source_ptp_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """)
        sync_layout.addWidget(self.source_ptp_combo, 0, 1)
        
        sync_layout.addWidget(QLabel("Цель PHC:"), 1, 0)
        self.target_ptp_combo = QComboBox()
        self.target_ptp_combo.addItems(["/dev/ptp0", "/dev/ptp1", "/dev/ptp2"])
        self.target_ptp_combo.setCurrentText("/dev/ptp0")
        self.target_ptp_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """)
        sync_layout.addWidget(self.target_ptp_combo, 1, 1)
        
        # Компенсация задержки для PHC2SYS
        sync_layout.addWidget(QLabel("Компенсация задержки (сек):"), 2, 0)
        self.phc_offset_seconds = QDoubleSpinBox()
        self.phc_offset_seconds.setRange(-1.0, 1.0)
        self.phc_offset_seconds.setDecimals(9)
        self.phc_offset_seconds.setSingleStep(0.000000001)
        self.phc_offset_seconds.setValue(0.0)
        self.phc_offset_seconds.setStyleSheet("""
            QDoubleSpinBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QDoubleSpinBox:focus {
                border-color: #3498db;
            }
        """)
        sync_layout.addWidget(self.phc_offset_seconds, 2, 1)
        
        sync_layout.addWidget(QLabel("Компенсация задержки (нс):"), 3, 0)
        self.phc_offset_nanoseconds = QSpinBox()
        self.phc_offset_nanoseconds.setRange(-999999999, 999999999)
        self.phc_offset_nanoseconds.setValue(0)
        self.phc_offset_nanoseconds.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        sync_layout.addWidget(self.phc_offset_nanoseconds, 3, 1)
        
        sync_layout.addWidget(QLabel("Скорость коррекции:"), 4, 0)
        self.phc_rate = QDoubleSpinBox()
        self.phc_rate.setRange(0.0, 1.0)
        self.phc_rate.setDecimals(3)
        self.phc_rate.setSingleStep(0.001)
        self.phc_rate.setValue(0.0)
        self.phc_rate.setStyleSheet("""
            QDoubleSpinBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QDoubleSpinBox:focus {
                border-color: #3498db;
            }
        """)
        sync_layout.addWidget(self.phc_rate, 4, 1)
        
        self.start_phc_btn = ModernButton("Запустить PHC2SYS")
        self.start_phc_btn.clicked.connect(self.start_phc_sync)
        sync_layout.addWidget(self.start_phc_btn, 0, 2)
        
        self.stop_phc_btn = DangerButton("Остановить PHC2SYS")
        self.stop_phc_btn.clicked.connect(self.stop_phc_sync)
        sync_layout.addWidget(self.stop_phc_btn, 1, 2)
        
        # TS2PHC синхронизация
        sync_layout.addWidget(QLabel("TS2PHC устройство:"), 5, 0)
        self.ts2phc_ptp_combo = QComboBox()
        self.ts2phc_ptp_combo.addItems(["/dev/ptp0", "/dev/ptp1", "/dev/ptp2"])
        self.ts2phc_ptp_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """)
        sync_layout.addWidget(self.ts2phc_ptp_combo, 5, 1)
        
        # Компенсация задержки для TS2PHC
        sync_layout.addWidget(QLabel("TS2PHC задержка (сек):"), 6, 0)
        self.ts2phc_offset_seconds = QDoubleSpinBox()
        self.ts2phc_offset_seconds.setRange(-1.0, 1.0)
        self.ts2phc_offset_seconds.setDecimals(9)
        self.ts2phc_offset_seconds.setSingleStep(0.000000001)
        self.ts2phc_offset_seconds.setValue(0.0)
        self.ts2phc_offset_seconds.setStyleSheet("""
            QDoubleSpinBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QDoubleSpinBox:focus {
                border-color: #3498db;
            }
        """)
        sync_layout.addWidget(self.ts2phc_offset_seconds, 6, 1)
        
        sync_layout.addWidget(QLabel("TS2PHC задержка (нс):"), 7, 0)
        self.ts2phc_offset_nanoseconds = QSpinBox()
        self.ts2phc_offset_nanoseconds.setRange(-999999999, 999999999)
        self.ts2phc_offset_nanoseconds.setValue(0)
        self.ts2phc_offset_nanoseconds.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        sync_layout.addWidget(self.ts2phc_offset_nanoseconds, 7, 1)
        
        self.start_ts2phc_btn = ModernButton("Запустить TS2PHC")
        self.start_ts2phc_btn.clicked.connect(self.start_ts2phc_sync)
        sync_layout.addWidget(self.start_ts2phc_btn, 5, 2)
        
        self.stop_ts2phc_btn = DangerButton("Остановить TS2PHC")
        self.stop_ts2phc_btn.clicked.connect(self.stop_ts2phc_sync)
        sync_layout.addWidget(self.stop_ts2phc_btn, 6, 2)
        
        # Статус синхронизации
        self.sync_status_label = QLabel("Статус: Не синхронизировано")
        self.sync_status_label.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 10px;")
        sync_layout.addWidget(self.sync_status_label, 8, 0, 1, 3)
        
        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)
        
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
            """
            self.info_text.setText(info_text.strip())
            
            # Обновляем статус синхронизации
            self.update_sync_status()
    
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
            # Сигнализируем главному окну об обновлении таблиц
            if hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'refresh_data'):
                self.parent().parent().refresh_data()
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
            # Сигнализируем главному окну об обновлении таблиц
            if hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'refresh_data'):
                self.parent().parent().refresh_data()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось изменить настройки TCXO")
    
    def start_phc_sync(self):
        """Запуск PHC2SYS синхронизации"""
        source_ptp = self.source_ptp_combo.currentText()
        target_ptp = self.target_ptp_combo.currentText()
        
        if source_ptp == target_ptp:
            QMessageBox.warning(self, "Ошибка", "Источник и цель не могут быть одинаковыми")
            return
        
        # Получаем значения компенсации задержки
        offset_seconds = self.phc_offset_seconds.value()
        offset_nanoseconds = self.phc_offset_nanoseconds.value()
        rate = self.phc_rate.value()
        
        # Валидация
        if abs(offset_seconds) > 1.0:
            QMessageBox.warning(self, "Ошибка", "Компенсация задержки (сек) должна быть в диапазоне ±1.0")
            return
        
        if abs(offset_nanoseconds) > 999999999:
            QMessageBox.warning(self, "Ошибка", "Компенсация задержки (нс) должна быть в диапазоне ±999,999,999")
            return
        
        if rate < 0.0 or rate > 1.0:
            QMessageBox.warning(self, "Ошибка", "Скорость коррекции должна быть в диапазоне 0.0-1.0")
            return
        
        # Вычисляем общую задержку в наносекундах
        total_offset_ns = int(offset_seconds * 1_000_000_000) + offset_nanoseconds
        
        success = self.nic_manager.start_phc_to_phc_sync(source_ptp, target_ptp, total_offset_ns, rate)
        
        if success:
            offset_text = f" (задержка: {total_offset_ns} нс, скорость: {rate})" if total_offset_ns != 0 or rate != 0.0 else ""
            QMessageBox.information(self, "Успех", f"PHC2SYS синхронизация запущена: {source_ptp} -> {target_ptp}{offset_text}")
            self.update_sync_status()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось запустить PHC2SYS синхронизацию")
    
    def stop_phc_sync(self):
        """Остановка PHC2SYS синхронизации"""
        success = self.nic_manager.stop_phc_sync()
        
        if success:
            QMessageBox.information(self, "Успех", "PHC2SYS синхронизация остановлена")
            self.update_sync_status()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось остановить PHC2SYS синхронизацию")
    
    def start_ts2phc_sync(self):
        """Запуск TS2PHC синхронизации"""
        nic_name = self.nic_combo.currentText()
        if not nic_name:
            QMessageBox.warning(self, "Ошибка", "Выберите NIC карту")
            return
        
        ptp_device = self.ts2phc_ptp_combo.currentText()
        
        # Получаем значения компенсации задержки для TS2PHC
        offset_seconds = self.ts2phc_offset_seconds.value()
        offset_nanoseconds = self.ts2phc_offset_nanoseconds.value()
        
        # Валидация
        if abs(offset_seconds) > 1.0:
            QMessageBox.warning(self, "Ошибка", "TS2PHC задержка (сек) должна быть в диапазоне ±1.0")
            return
        
        if abs(offset_nanoseconds) > 999999999:
            QMessageBox.warning(self, "Ошибка", "TS2PHC задержка (нс) должна быть в диапазоне ±999,999,999")
            return
        
        # Вычисляем общую задержку в наносекундах
        total_offset_ns = int(offset_seconds * 1_000_000_000) + offset_nanoseconds
        
        success = self.nic_manager.start_ts2phc_sync(nic_name, ptp_device, total_offset_ns)
        
        if success:
            offset_text = f" (задержка: {total_offset_ns} нс)" if total_offset_ns != 0 else ""
            QMessageBox.information(self, "Успех", f"TS2PHC синхронизация запущена для {nic_name}{offset_text}")
            self.update_sync_status()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось запустить TS2PHC синхронизацию")
    
    def stop_ts2phc_sync(self):
        """Остановка TS2PHC синхронизации"""
        success = self.nic_manager.stop_ts2phc_sync()
        
        if success:
            QMessageBox.information(self, "Успех", "TS2PHC синхронизация остановлена")
            self.update_sync_status()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось остановить TS2PHC синхронизацию")
    
    def update_sync_status(self):
        """Обновление статуса синхронизации"""
        status = self.nic_manager.get_sync_status()
        
        status_text = "Статус: "
        if status['phc2sys_running']:
            status_text += f"PHC2SYS запущен (PID: {status['phc2sys_pid']}) "
        if status['ts2phc_running']:
            status_text += f"TS2PHC запущен (PID: {status['ts2phc_pid']}) "
        if not status['phc2sys_running'] and not status['ts2phc_running']:
            status_text += "Не синхронизировано"
        
        self.sync_status_label.setText(status_text)


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
        phc_group = ModernGroupBox("PHC синхронизация")
        phc_layout = QGridLayout()
        phc_layout.setSpacing(15)
        
        self.phc_offset_label = QLabel("PHC Offset: N/A")
        self.phc_frequency_label = QLabel("PHC Frequency: N/A")
        phc_layout.addWidget(self.phc_offset_label, 0, 0)
        phc_layout.addWidget(self.phc_frequency_label, 0, 1)
        
        # Компенсация задержки для TimeNIC PHC
        phc_layout.addWidget(QLabel("Компенсация задержки (сек):"), 1, 0)
        self.timenic_phc_offset_seconds = QDoubleSpinBox()
        self.timenic_phc_offset_seconds.setRange(-1.0, 1.0)
        self.timenic_phc_offset_seconds.setDecimals(9)
        self.timenic_phc_offset_seconds.setSingleStep(0.000000001)
        self.timenic_phc_offset_seconds.setValue(0.0)
        self.timenic_phc_offset_seconds.setStyleSheet("""
            QDoubleSpinBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QDoubleSpinBox:focus {
                border-color: #3498db;
            }
        """)
        phc_layout.addWidget(self.timenic_phc_offset_seconds, 1, 1)
        
        phc_layout.addWidget(QLabel("Компенсация задержки (нс):"), 2, 0)
        self.timenic_phc_offset_nanoseconds = QSpinBox()
        self.timenic_phc_offset_nanoseconds.setRange(-999999999, 999999999)
        self.timenic_phc_offset_nanoseconds.setValue(0)
        self.timenic_phc_offset_nanoseconds.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        phc_layout.addWidget(self.timenic_phc_offset_nanoseconds, 2, 1)
        
        self.start_phc_btn = ModernButton("Запустить синхронизацию PHC")
        self.start_phc_btn.clicked.connect(self.start_phc_sync)
        phc_layout.addWidget(self.start_phc_btn, 3, 0, 1, 2)
        
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
            QMessageBox.warning(self, "Ошибка", "Выберите TimeNIC карту")
            return
        
        # Получаем значения компенсации задержки
        offset_seconds = self.timenic_phc_offset_seconds.value()
        offset_nanoseconds = self.timenic_phc_offset_nanoseconds.value()
        
        # Валидация
        if abs(offset_seconds) > 1.0:
            QMessageBox.warning(self, "Ошибка", "Компенсация задержки (сек) должна быть в диапазоне ±1.0")
            return
        
        if abs(offset_nanoseconds) > 999999999:
            QMessageBox.warning(self, "Ошибка", "Компенсация задержки (нс) должна быть в диапазоне ±999,999,999")
            return
        
        # Вычисляем общую задержку в наносекундах
        total_offset_ns = int(offset_seconds * 1_000_000_000) + offset_nanoseconds
        
        try:
            success = self.timenic_manager.start_phc_synchronization(timenic_name, total_offset_ns)
            if success:
                offset_text = f" (задержка: {total_offset_ns} нс)" if total_offset_ns != 0 else ""
                QMessageBox.information(self, "Успех", f"Синхронизация PHC запущена для {timenic_name}{offset_text}")
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
        

        
        # Обновляем графики
        self.traffic_ax.clear()
        if self.traffic_data['time']:
            self.traffic_ax.plot(self.traffic_data['time'], self.traffic_data['rx'], label='RX', color='blue')
            self.traffic_ax.plot(self.traffic_data['time'], self.traffic_data['tx'], label='TX', color='red')
            self.traffic_ax.legend()
            self.traffic_ax.set_title("Трафик (байт/с)")
            self.traffic_ax.set_xlabel("Время")
            self.traffic_ax.set_ylabel("Байт/с")
        

        
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
        

        
        # Обновляем графики
        self.timenic_traffic_ax.clear()
        if self.timenic_traffic_data['time']:
            self.timenic_traffic_ax.plot(self.timenic_traffic_data['time'], self.timenic_traffic_data['rx'], label='RX', color='blue')
            self.timenic_traffic_ax.plot(self.timenic_traffic_data['time'], self.timenic_traffic_data['tx'], label='TX', color='red')
            self.timenic_traffic_ax.legend()
            self.timenic_traffic_ax.set_title("Трафик (байт/с)")
            self.timenic_traffic_ax.set_xlabel("Время")
            self.timenic_traffic_ax.set_ylabel("Байт/с")
        

        
        self.timenic_traffic_canvas.draw()
    
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
    """Современное главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.nic_manager = IntelNICManager()
        self.timenic_manager = TimeNICManager()
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
    
    def setup_ui(self):
        """Настройка интерфейса главного окна"""
        self.setWindowTitle("SHIWA NIC-PPS Configuration and Monitoring Tool v1.2.0")
        
        # Адаптивный размер окна
        screen = QApplication.primaryScreen().availableGeometry()
        # Используем 90% от доступного размера экрана
        width = int(screen.width() * 0.9)
        height = int(screen.height() * 0.9)
        # Минимальный размер
        width = max(width, 1000)
        height = max(height, 700)
        # Максимальный размер
        width = min(width, 1600)
        height = min(height, 1200)
        
        # Центрируем окно
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.setGeometry(x, y, width, height)
        
        # Устанавливаем минимальный размер и делаем окно изменяемым
        self.setMinimumSize(800, 600)
        self.setMaximumSize(1920, 1080)  # Максимальный размер для больших мониторов
        self.resize(width, height)  # Устанавливаем начальный размер
        
        # Принудительно показываем окно
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Установка современного стиля для всего приложения
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
                color: #2c3e50;
            }
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                background-color: white;
                color: #2c3e50;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ecf0f1, stop:1 #bdc3c7);
                border: 1px solid #bdc3c7;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 12px 20px;
                margin-right: 2px;
                font-weight: bold;
                color: #2c3e50;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
            }
            QTabBar::tab:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5dade2, stop:1 #3498db);
                color: white;
            }
        """)
        
        # Создаем центральный виджет с прокруткой
        central_widget = QWidget()
        scroll_area = QScrollArea()
        scroll_area.setWidget(central_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Стили для прокрутки
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #ecf0f1;
            }
            QScrollBar:vertical {
                background-color: #bdc3c7;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #7f8c8d;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5d6d7e;
            }
            QScrollBar:horizontal {
                background-color: #bdc3c7;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #7f8c8d;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #5d6d7e;
            }
        """)
        
        self.setCentralWidget(scroll_area)
        
        # Создаем вкладки
        tab_widget = QTabWidget()
        tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        
        # Вкладка с таблицей NIC карт
        self.nic_table = NICTableWidget()
        tab_widget.addTab(self.nic_table, "📡 NIC карты")
        
        # Вкладка с таблицей TimeNIC карт
        self.timenic_table = TimeNICTableWidget()
        tab_widget.addTab(self.timenic_table, "⏰ TimeNIC карты")
        
        # Вкладка конфигурации
        self.config_widget = ConfigurationWidget(self.nic_manager)
        tab_widget.addTab(self.config_widget, "⚙️ Конфигурация")
        
        # Вкладка конфигурации TimeNIC
        self.timenic_config_widget = TimeNICConfigurationWidget(self.timenic_manager)
        tab_widget.addTab(self.timenic_config_widget, "🔧 Конфигурация TimeNIC")
        
        # Вкладка мониторинга
        self.monitor_widget = MonitoringWidget(self.nic_manager, self.timenic_manager)
        tab_widget.addTab(self.monitor_widget, "📊 Мониторинг")
        
        # Основной layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(tab_widget)
        
        # Панель управления
        control_panel = QFrame()
        control_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34495e, stop:1 #2c3e50);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        control_layout = QHBoxLayout(control_panel)
        
        # Информация о системе
        system_info = QLabel("SHIWA NIC-PPS v1.2.0 | Система мониторинга активна")
        system_info.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        control_layout.addWidget(system_info)
        
        control_layout.addStretch()
        
        # Кнопки управления
        refresh_btn = ModernButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.refresh_data)
        control_layout.addWidget(refresh_btn)
        
        export_btn = ModernButton("📤 Экспорт")
        export_btn.clicked.connect(self.export_data)
        control_layout.addWidget(export_btn)
        
        layout.addWidget(control_panel)
        central_widget.setLayout(layout)
        
        # Таймер для обновления данных
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_data)
        self.update_timer.start(5000)  # Обновление каждые 5 секунд
        
        # Первоначальное обновление
        self.refresh_data()
    
    def setup_menu(self):
        """Настройка меню"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #34495e;
                color: white;
                border: none;
                font-weight: bold;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 16px;
            }
            QMenuBar::item:selected {
                background-color: #3498db;
            }
            QMenu {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
            }
            QMenu::item {
                padding: 8px 20px;
                color: #2c3e50;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # Файл меню
        file_menu = menubar.addMenu("Файл")
        file_menu.addAction("Экспорт данных", self.export_data)
        file_menu.addSeparator()
        file_menu.addAction("Выход", self.close)
        
        # Настройки меню
        settings_menu = menubar.addMenu("Настройки")
        settings_menu.addAction("Обновить данные", self.refresh_data)
        settings_menu.addAction("Очистить кэш", self.clear_cache)
        
        # Справка меню
        help_menu = menubar.addMenu("Справка")
        help_menu.addAction("О программе", self.show_about)
    
    def setup_status_bar(self):
        """Настройка строки состояния"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Индикатор подключения
        self.connection_indicator = StatusIndicator()
        self.connection_indicator.set_status("up")
        
        # Информация о статусе
        self.status_label = QLabel("Система готова к работе")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        
        # Счетчик обновлений
        self.update_counter = QLabel("Обновлений: 0")
        self.update_counter.setStyleSheet("color: #7f8c8d;")
        
        self.status_bar.addWidget(self.connection_indicator)
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.update_counter)
    
    def export_data(self):
        """Экспорт данных"""
        QMessageBox.information(self, "Экспорт", "Функция экспорта будет реализована в следующей версии")
    
    def clear_cache(self):
        """Очистка кэша"""
        QMessageBox.information(self, "Кэш", "Кэш очищен")
    
    def show_about(self):
        """Показать информацию о программе"""
        QMessageBox.about(self, "О программе", 
                         "SHIWA NIC-PPS Configuration and Monitoring Tool v1.2.0\n\n"
                         "Современный инструмент для конфигурации и мониторинга\n"
                         "Intel NIC карт с поддержкой PPS и TimeNIC.\n\n"
                         "© 2025 SHIWA Technologies")
    
    def refresh_data(self):
        """Обновление данных"""
        try:
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
            
            # Обновляем счетчик
            if hasattr(self, 'update_counter'):
                current_count = int(self.update_counter.text().split(': ')[1])
                self.update_counter.setText(f"Обновлений: {current_count + 1}")
            
            # Обновляем статус
            if hasattr(self, 'status_label'):
                self.status_label.setText("Данные обновлены")
                self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            
            # Проверяем и перезапускаем phc2sys если нужно
            self.check_and_restart_phc_sync()
                
        except Exception as e:
            # Обновляем статус при ошибке
            if hasattr(self, 'status_label'):
                self.status_label.setText(f"Ошибка обновления: {str(e)}")
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
    
    def check_and_restart_phc_sync(self):
        """Проверка и перезапуск синхронизации PHC если процесс упал"""
        try:
            if not self.nic_manager.is_phc_sync_running():
                # Получаем текущие настройки синхронизации
                source_ptp = self.config_widget.source_ptp_combo.currentText()
                target_ptp = self.config_widget.target_ptp_combo.currentText()
                
                if source_ptp and target_ptp and source_ptp != target_ptp:
                    print("🔄 Автоматический перезапуск синхронизации PHC...")
                    offset_seconds = self.config_widget.phc_offset_seconds.value()
                    offset_nanoseconds = self.config_widget.phc_offset_nanoseconds.value()
                    total_offset_ns = int(offset_seconds * 1_000_000_000 + offset_nanoseconds)
                    rate = self.config_widget.phc_rate.value()
                    
                    # Используем улучшенный метод перезапуска с автоматическим исправлением направления
                    self.nic_manager.restart_phc_sync_if_needed(
                        source_ptp, target_ptp, total_offset_ns, rate
                    )
        except Exception as e:
            print(f"Ошибка проверки синхронизации PHC: {e}")


def main():
    """Главная функция"""
    app = QApplication(sys.argv)
    
    # Настройка стиля приложения
    app.setStyle('Fusion')
    
    # Установка иконки приложения (если есть)
    app.setApplicationName("SHIWA NIC-PPS")
    app.setApplicationVersion("1.2.0")
    app.setOrganizationName("SHIWA Technologies")
    
    # Глобальные стили для приложения
    app.setStyleSheet("""
        QApplication {
            font-family: 'Segoe UI', 'Arial', sans-serif;
            font-size: 12px;
            color: #2c3e50;
            background-color: #ecf0f1;
        }
        QWidget {
            color: #2c3e50;
            background-color: #ecf0f1;
        }
        QLabel {
            color: #2c3e50;
            background-color: transparent;
        }
        QGroupBox {
            color: #2c3e50;
            background-color: white;
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #2c3e50;
            background-color: white;
        }
        QComboBox {
            color: #2c3e50;
            background-color: white;
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            padding: 8px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #2c3e50;
            margin-right: 5px;
        }
        QSpinBox, QDoubleSpinBox {
            color: #2c3e50;
            background-color: white;
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            padding: 8px;
        }
        QCheckBox {
            color: #2c3e50;
            background-color: transparent;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #bdc3c7;
            border-radius: 3px;
            background-color: white;
        }
        QCheckBox::indicator:checked {
            background-color: #3498db;
            border-color: #2980b9;
        }
        QTableWidget {
            color: #2c3e50;
            background-color: white;
            gridline-color: #bdc3c7;
            border: 1px solid #bdc3c7;
            border-radius: 6px;
        }
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #ecf0f1;
        }
        QTableWidget::item:selected {
            background-color: #3498db;
            color: white;
        }
        QHeaderView::section {
            background-color: #34495e;
            color: white;
            padding: 8px;
            border: none;
            font-weight: bold;
        }
        QMessageBox {
            background-color: white;
            border: 1px solid #bdc3c7;
            border-radius: 8px;
            color: #2c3e50;
        }
        QMessageBox QLabel {
            color: #2c3e50;
            background-color: transparent;
        }
        QMessageBox QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #3498db, stop:1 #2980b9);
            border: none;
            border-radius: 6px;
            color: white;
            font-weight: bold;
            padding: 8px 16px;
            min-width: 80px;
        }
        QMessageBox QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #5dade2, stop:1 #3498db);
        }
    """)
    
    # Создание и отображение главного окна
    window = MainWindow()
    window.show()
    
    # Центрирование окна на экране
    screen = app.primaryScreen().geometry()
    window_geometry = window.geometry()
    x = (screen.width() - window_geometry.width()) // 2
    y = (screen.height() - window_geometry.height()) // 2
    window.move(x, y)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()