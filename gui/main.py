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


class MonitoringThread(QThread):
    """Поток для мониторинга в фоновом режиме"""
    data_updated = pyqtSignal(dict)
    
    def __init__(self, nic_manager: IntelNICManager):
        super().__init__()
        self.nic_manager = nic_manager
        self.running = True
    
    def run(self):
        while self.running:
            try:
                # Обновляем данные каждую секунду
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
            
            # TCXO с чекбоксом
            tcxo_item = QTableWidgetItem()
            tcxo_item.setCheckState(Qt.CheckState.Checked if nic.tcxo_enabled else Qt.CheckState.Unchecked)
            self.setItem(row, 7, tcxo_item)
            
            # Температура
            temp_text = f"{nic.temperature:.1f}°C" if nic.temperature else "N/A"
            self.setItem(row, 8, QTableWidgetItem(temp_text))
        
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
            self.update_nic_list()
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
            self.update_nic_list()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось изменить настройки TCXO")


class MonitoringWidget(QWidget):
    """Виджет для мониторинга производительности"""
    
    def __init__(self, nic_manager: IntelNICManager):
        super().__init__()
        self.nic_manager = nic_manager
        self.monitoring_data = {}
        self.setup_ui()
        
        # Запускаем поток мониторинга
        self.monitoring_thread = MonitoringThread(nic_manager)
        self.monitoring_thread.data_updated.connect(self.update_monitoring_data)
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
        
        # Графики
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # График трафика
        traffic_group = QGroupBox("Трафик")
        self.traffic_canvas = self.create_traffic_chart()
        traffic_group.setLayout(QVBoxLayout())
        traffic_group.layout().addWidget(self.traffic_canvas)
        splitter.addWidget(traffic_group)
        
        # График температуры
        temp_group = QGroupBox("Температура")
        self.temp_canvas = self.create_temperature_chart()
        temp_group.setLayout(QVBoxLayout())
        temp_group.layout().addWidget(self.temp_canvas)
        splitter.addWidget(temp_group)
        
        layout.addWidget(splitter)
        
        # Статистика
        stats_group = QGroupBox("Статистика")
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(100)
        self.stats_text.setReadOnly(True)
        stats_group.setLayout(QVBoxLayout())
        stats_group.layout().addWidget(self.stats_text)
        layout.addWidget(stats_group)
        
        self.setLayout(layout)
        
        # Обновляем список NIC карт
        self.update_monitor_nic_list()
    
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
    
    def update_monitor_nic_list(self):
        """Обновление списка NIC карт для мониторинга"""
        self.monitor_nic_combo.clear()
        nics = self.nic_manager.get_all_nics()
        for nic in nics:
            self.monitor_nic_combo.addItem(nic.name)
    
    def on_monitor_nic_selected(self, nic_name: str):
        """Обработчик выбора NIC для мониторинга"""
        if nic_name:
            # Очищаем данные при смене карты
            self.traffic_data = {'rx': [], 'tx': [], 'time': []}
            self.temp_data = {'temp': [], 'time': []}
            self.update_charts()
    
    def update_monitoring_data(self, data: dict):
        """Обновление данных мониторинга"""
        self.monitoring_data = data
        self.update_charts()
        self.update_stats()
    
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
        
        self.traffic_canvas.draw()
        self.temp_canvas.draw()
    
    def update_stats(self):
        """Обновление статистики"""
        current_nic = self.monitor_nic_combo.currentText()
        if not current_nic or current_nic not in self.monitoring_data:
            return
        
        data = self.monitoring_data[current_nic]
        stats_text = ""
        
        if 'stats' in data:
            stats = data['stats']
            stats_text += f"Принято пакетов: {stats.get('rx_packets', 0):,}\n"
            stats_text += f"Отправлено пакетов: {stats.get('tx_packets', 0):,}\n"
            stats_text += f"Ошибки приема: {stats.get('rx_errors', 0):,}\n"
            stats_text += f"Ошибки отправки: {stats.get('tx_errors', 0):,}\n"
            stats_text += f"Отброшено при приеме: {stats.get('rx_dropped', 0):,}\n"
            stats_text += f"Отброшено при отправке: {stats.get('tx_dropped', 0):,}\n"
        
        if 'temperature' in data and data['temperature']:
            stats_text += f"Температура: {data['temperature']:.1f}°C\n"
        
        if 'status' in data:
            stats_text += f"Статус: {data['status']}"
        
        self.stats_text.setText(stats_text)
    
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
        
        # Вкладка конфигурации
        self.config_widget = ConfigurationWidget(self.nic_manager)
        tab_widget.addTab(self.config_widget, "Конфигурация")
        
        # Вкладка мониторинга
        self.monitor_widget = MonitoringWidget(self.nic_manager)
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
        nics = self.nic_manager.get_all_nics()
        self.nic_table.update_data(nics)
        self.config_widget.update_nic_list()
        self.monitor_widget.update_monitor_nic_list()


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