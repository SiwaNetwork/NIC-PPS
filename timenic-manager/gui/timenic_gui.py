#!/usr/bin/env python3
"""
TimeNIC GUI - Graphical User Interface for TimeNIC Management
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Optional
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QGridLayout, QTextEdit,
    QComboBox, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QProgressBar, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QDateTime
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QColor, QFont

from common.timenic_core import TimeNICManager, PTMStatus, SyncStatus


class SyncMonitorThread(QThread):
    """Thread for monitoring synchronization status"""
    status_update = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, manager: TimeNICManager, pin_index: int = 1):
        super().__init__()
        self.manager = manager
        self.pin_index = pin_index
        self.process = None
        self.running = False
        
    def run(self):
        self.running = True
        try:
            self.process = self.manager.sync_to_external_pps(self.pin_index)
            
            while self.running and self.process:
                output = self.process.stdout.readline()
                if output:
                    sync_status = self.manager.get_sync_status(output)
                    if sync_status:
                        self.status_update.emit({
                            'is_synced': sync_status.is_synced,
                            'offset_ns': sync_status.offset_ns,
                            'frequency_ppb': sync_status.frequency_ppb,
                            'rms_ns': sync_status.rms_ns,
                            'timestamp': sync_status.last_update
                        })
                
                if self.process.poll() is not None:
                    self.error_occurred.emit("ts2phc process terminated")
                    break
                    
        except Exception as e:
            self.error_occurred.emit(str(e))
            
    def stop(self):
        self.running = False
        if self.process:
            self.process.terminate()
            self.process = None


class TimeNICGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = TimeNICManager()
        self.sync_thread = None
        self.init_ui()
        self.setup_timers()
        
    def init_ui(self):
        self.setWindowTitle("TimeNIC Manager")
        self.setGeometry(100, 100, 900, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_status_tab(), "Status")
        self.tabs.addTab(self.create_control_tab(), "Control")
        self.tabs.addTab(self.create_sync_tab(), "Synchronization")
        self.tabs.addTab(self.create_config_tab(), "Configuration")
        self.tabs.addTab(self.create_log_tab(), "Logs")
        
        main_layout.addWidget(self.tabs)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.update_status_bar("Ready")
        
    def create_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        
        # Title
        title = QLabel("TimeNIC Manager")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        
        # Connection status
        self.connection_label = QLabel("● Disconnected")
        self.connection_label.setStyleSheet("color: red;")
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.connection_label)
        
        return header
        
    def create_status_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Device info group
        device_group = QGroupBox("Device Information")
        device_layout = QGridLayout()
        
        self.device_labels = {
            'interface': QLabel("N/A"),
            'ptp_device': QLabel("N/A"),
            'clock_index': QLabel("N/A"),
            'capabilities': QLabel("N/A")
        }
        
        device_layout.addWidget(QLabel("Interface:"), 0, 0)
        device_layout.addWidget(self.device_labels['interface'], 0, 1)
        device_layout.addWidget(QLabel("PTP Device:"), 1, 0)
        device_layout.addWidget(self.device_labels['ptp_device'], 1, 1)
        device_layout.addWidget(QLabel("Clock Index:"), 2, 0)
        device_layout.addWidget(self.device_labels['clock_index'], 2, 1)
        device_layout.addWidget(QLabel("Capabilities:"), 3, 0)
        device_layout.addWidget(self.device_labels['capabilities'], 3, 1)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # Status indicators
        status_group = QGroupBox("Status Indicators")
        status_layout = QGridLayout()
        
        self.status_indicators = {
            'pps_output': self.create_status_indicator("PPS Output (SMA1)"),
            'pps_input': self.create_status_indicator("PPS Input (SMA2)"),
            'sync': self.create_status_indicator("Synchronization"),
            'ptm': self.create_status_indicator("PTM Support")
        }
        
        row = 0
        for name, (label, indicator) in self.status_indicators.items():
            status_layout.addWidget(label, row, 0)
            status_layout.addWidget(indicator, row, 1)
            row += 1
            
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # PHC Time
        time_group = QGroupBox("PHC Time")
        time_layout = QVBoxLayout()
        
        self.phc_time_label = QLabel("--:--:--")
        self.phc_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_font = QFont()
        time_font.setPointSize(20)
        self.phc_time_label.setFont(time_font)
        
        time_layout.addWidget(self.phc_time_label)
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Status")
        refresh_btn.clicked.connect(self.refresh_status)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        return widget
        
    def create_control_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # PPS Output Control
        output_group = QGroupBox("PPS Output Control (SMA1)")
        output_layout = QVBoxLayout()
        
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Frequency (Hz):"))
        self.freq_spinbox = QSpinBox()
        self.freq_spinbox.setRange(1, 1000000)
        self.freq_spinbox.setValue(1)
        freq_layout.addWidget(self.freq_spinbox)
        
        self.enable_output_btn = QPushButton("Enable PPS Output")
        self.enable_output_btn.clicked.connect(self.enable_pps_output)
        
        output_layout.addLayout(freq_layout)
        output_layout.addWidget(self.enable_output_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # PPS Input Control
        input_group = QGroupBox("PPS Input Control (SMA2)")
        input_layout = QVBoxLayout()
        
        self.enable_input_btn = QPushButton("Enable PPS Input")
        self.enable_input_btn.clicked.connect(self.enable_pps_input)
        
        self.read_events_btn = QPushButton("Read PPS Events (5)")
        self.read_events_btn.clicked.connect(self.read_pps_events)
        
        input_layout.addWidget(self.enable_input_btn)
        input_layout.addWidget(self.read_events_btn)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # PTM Control
        ptm_group = QGroupBox("PTM Control")
        ptm_layout = QVBoxLayout()
        
        pci_layout = QHBoxLayout()
        pci_layout.addWidget(QLabel("PCI Address:"))
        self.pci_address = QComboBox()
        self.pci_address.setEditable(True)
        pci_layout.addWidget(self.pci_address)
        
        self.enable_ptm_btn = QPushButton("Enable PTM")
        self.enable_ptm_btn.clicked.connect(self.enable_ptm)
        
        ptm_layout.addLayout(pci_layout)
        ptm_layout.addWidget(self.enable_ptm_btn)
        ptm_group.setLayout(ptm_layout)
        layout.addWidget(ptm_group)
        
        # Quick Setup
        setup_btn = QPushButton("Run Quick Setup")
        setup_btn.clicked.connect(self.run_quick_setup)
        layout.addWidget(setup_btn)
        
        layout.addStretch()
        return widget
        
    def create_sync_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Sync control
        control_group = QGroupBox("Synchronization Control")
        control_layout = QVBoxLayout()
        
        pin_layout = QHBoxLayout()
        pin_layout.addWidget(QLabel("Pin Index:"))
        self.pin_spinbox = QSpinBox()
        self.pin_spinbox.setRange(0, 3)
        self.pin_spinbox.setValue(1)
        pin_layout.addWidget(self.pin_spinbox)
        
        self.sync_btn = QPushButton("Start Synchronization")
        self.sync_btn.clicked.connect(self.toggle_sync)
        
        control_layout.addLayout(pin_layout)
        control_layout.addWidget(self.sync_btn)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Sync status
        status_group = QGroupBox("Synchronization Status")
        status_layout = QGridLayout()
        
        self.sync_labels = {
            'status': QLabel("Not Running"),
            'offset': QLabel("--"),
            'frequency': QLabel("--"),
            'rms': QLabel("--")
        }
        
        status_layout.addWidget(QLabel("Status:"), 0, 0)
        status_layout.addWidget(self.sync_labels['status'], 0, 1)
        status_layout.addWidget(QLabel("Offset:"), 1, 0)
        status_layout.addWidget(self.sync_labels['offset'], 1, 1)
        status_layout.addWidget(QLabel("Frequency:"), 2, 0)
        status_layout.addWidget(self.sync_labels['frequency'], 2, 1)
        status_layout.addWidget(QLabel("RMS:"), 3, 0)
        status_layout.addWidget(self.sync_labels['rms'], 3, 1)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Sync graph placeholder
        graph_group = QGroupBox("Synchronization Graph")
        graph_layout = QVBoxLayout()
        graph_label = QLabel("Graph visualization would go here")
        graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        graph_label.setMinimumHeight(200)
        graph_layout.addWidget(graph_label)
        graph_group.setLayout(graph_layout)
        layout.addWidget(graph_group)
        
        layout.addStretch()
        return widget
        
    def create_config_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Interface selection
        interface_group = QGroupBox("Interface Configuration")
        interface_layout = QGridLayout()
        
        interface_layout.addWidget(QLabel("Network Interface:"), 0, 0)
        self.interface_combo = QComboBox()
        self.interface_combo.addItems(["enp3s0", "enp1s0", "eth0", "eth1"])
        self.interface_combo.setEditable(True)
        self.interface_combo.setCurrentText(self.manager.interface)
        interface_layout.addWidget(self.interface_combo, 0, 1)
        
        interface_layout.addWidget(QLabel("PTP Device:"), 1, 0)
        self.ptp_device_combo = QComboBox()
        self.ptp_device_combo.addItems(["/dev/ptp0", "/dev/ptp1", "/dev/ptp2"])
        self.ptp_device_combo.setEditable(True)
        self.ptp_device_combo.setCurrentText(self.manager.ptp_device)
        interface_layout.addWidget(self.ptp_device_combo, 1, 1)
        
        apply_btn = QPushButton("Apply Configuration")
        apply_btn.clicked.connect(self.apply_config)
        interface_layout.addWidget(apply_btn, 2, 0, 1, 2)
        
        interface_group.setLayout(interface_layout)
        layout.addWidget(interface_group)
        
        # Driver installation
        driver_group = QGroupBox("Driver Management")
        driver_layout = QVBoxLayout()
        
        install_driver_btn = QPushButton("Install Patched Driver")
        install_driver_btn.clicked.connect(self.install_driver)
        driver_layout.addWidget(install_driver_btn)
        
        driver_info = QLabel("Note: Driver installation requires root privileges and system reboot")
        driver_info.setWordWrap(True)
        driver_layout.addWidget(driver_info)
        
        driver_group.setLayout(driver_layout)
        layout.addWidget(driver_group)
        
        # Export/Import
        export_group = QGroupBox("Configuration Export/Import")
        export_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export Config")
        export_btn.clicked.connect(self.export_config)
        export_layout.addWidget(export_btn)
        
        import_btn = QPushButton("Import Config")
        import_btn.clicked.connect(self.import_config)
        export_layout.addWidget(import_btn)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        return widget
        
    def create_log_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)
        
        # Log controls
        controls_layout = QHBoxLayout()
        
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_cb)
        
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.log_display.clear)
        controls_layout.addWidget(clear_btn)
        
        save_btn = QPushButton("Save Logs")
        save_btn.clicked.connect(self.save_logs)
        controls_layout.addWidget(save_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        return widget
        
    def create_status_indicator(self, label_text: str) -> tuple:
        label = QLabel(label_text + ":")
        indicator = QLabel("●")
        indicator.setStyleSheet("color: gray;")
        return label, indicator
        
    def setup_timers(self):
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # Update every 5 seconds
        
        # PHC time update timer
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_phc_time)
        self.time_timer.start(1000)  # Update every second
        
        # Initial update
        self.refresh_status()
        
    def log_message(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        self.log_display.append(log_entry)
        
        if self.auto_scroll_cb.isChecked():
            self.log_display.verticalScrollBar().setValue(
                self.log_display.verticalScrollBar().maximum()
            )
            
    def update_status_bar(self, message: str):
        self.status_bar.showMessage(message)
        
    def refresh_status(self):
        self.log_message("Refreshing device status...")
        status = self.manager.get_status()
        
        # Update device info
        if status['device']:
            device = status['device']
            self.device_labels['interface'].setText(device['interface'])
            self.device_labels['ptp_device'].setText(device['ptp_device'])
            self.device_labels['clock_index'].setText(str(device['clock_index']))
            self.device_labels['capabilities'].setText(", ".join(device['capabilities']))
            
            self.connection_label.setText("● Connected")
            self.connection_label.setStyleSheet("color: green;")
        else:
            self.connection_label.setText("● Disconnected")
            self.connection_label.setStyleSheet("color: red;")
            
        # Update status indicators
        self.update_indicator('pps_output', status['pps_output']['enabled'])
        self.update_indicator('pps_input', status['pps_input']['enabled'])
        self.update_indicator('sync', False)  # Will be updated by sync thread
        
        # PTM status
        ptm_status = status['ptm_status']
        if ptm_status == "ENABLED":
            self.update_indicator('ptm', True)
        elif ptm_status == "DISABLED":
            self.update_indicator('ptm', False, "yellow")
        else:
            self.update_indicator('ptm', False)
            
        self.log_message("Status refresh completed")
        
    def update_indicator(self, name: str, enabled: bool, color: str = None):
        if name in self.status_indicators:
            _, indicator = self.status_indicators[name]
            if enabled:
                indicator.setStyleSheet("color: green;")
            else:
                indicator.setStyleSheet(f"color: {color or 'red'};")
                
    def update_phc_time(self):
        phc_time = self.manager.get_phc_time()
        if phc_time:
            time_str = datetime.fromtimestamp(phc_time).strftime("%H:%M:%S")
            self.phc_time_label.setText(time_str)
            
    def update_status(self):
        # Quick status check
        device = self.manager.check_device()
        if device:
            self.connection_label.setText("● Connected")
            self.connection_label.setStyleSheet("color: green;")
        else:
            self.connection_label.setText("● Disconnected")
            self.connection_label.setStyleSheet("color: red;")
            
    def enable_pps_output(self):
        frequency = self.freq_spinbox.value()
        self.log_message(f"Enabling PPS output at {frequency} Hz...")
        
        if self.manager.enable_pps_output(int(1e9 / frequency)):
            self.log_message(f"PPS output enabled at {frequency} Hz", "SUCCESS")
            self.update_indicator('pps_output', True)
            QMessageBox.information(self, "Success", f"PPS output enabled at {frequency} Hz")
        else:
            self.log_message("Failed to enable PPS output", "ERROR")
            QMessageBox.critical(self, "Error", "Failed to enable PPS output")
            
    def enable_pps_input(self):
        self.log_message("Enabling PPS input...")
        
        if self.manager.enable_pps_input():
            self.log_message("PPS input enabled", "SUCCESS")
            self.update_indicator('pps_input', True)
            QMessageBox.information(self, "Success", "PPS input enabled on SMA2")
        else:
            self.log_message("Failed to enable PPS input", "ERROR")
            QMessageBox.critical(self, "Error", "Failed to enable PPS input")
            
    def read_pps_events(self):
        self.log_message("Reading PPS events...")
        timestamps = self.manager.read_pps_events(5)
        
        if timestamps:
            msg = "PPS Events:\n"
            for i, ts in enumerate(timestamps):
                time_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S.%f')
                msg += f"Event {i+1}: {time_str}\n"
                self.log_message(f"PPS Event {i+1}: {ts:.9f}")
            QMessageBox.information(self, "PPS Events", msg)
        else:
            self.log_message("No PPS events received", "WARNING")
            QMessageBox.warning(self, "No Events", "No PPS events received. Check connection.")
            
    def enable_ptm(self):
        pci_address = self.pci_address.currentText()
        if not pci_address:
            QMessageBox.warning(self, "Error", "Please enter PCI address")
            return
            
        self.log_message(f"Enabling PTM for {pci_address}...")
        
        if self.manager.enable_ptm(pci_address):
            self.log_message("PTM enabled successfully", "SUCCESS")
            self.update_indicator('ptm', True)
            QMessageBox.information(self, "Success", "PTM enabled successfully")
        else:
            self.log_message("Failed to enable PTM", "ERROR")
            QMessageBox.critical(self, "Error", "Failed to enable PTM")
            
    def toggle_sync(self):
        if self.sync_thread and self.sync_thread.isRunning():
            # Stop sync
            self.sync_thread.stop()
            self.sync_thread.wait()
            self.sync_thread = None
            self.sync_btn.setText("Start Synchronization")
            self.update_indicator('sync', False)
            self.log_message("Synchronization stopped")
        else:
            # Start sync
            pin_index = self.pin_spinbox.value()
            self.log_message(f"Starting synchronization on pin {pin_index}...")
            
            self.sync_thread = SyncMonitorThread(self.manager, pin_index)
            self.sync_thread.status_update.connect(self.update_sync_status)
            self.sync_thread.error_occurred.connect(self.sync_error)
            self.sync_thread.start()
            
            self.sync_btn.setText("Stop Synchronization")
            self.update_indicator('sync', True)
            
    def update_sync_status(self, status: dict):
        if status['is_synced']:
            self.sync_labels['status'].setText("SYNCED")
            self.sync_labels['status'].setStyleSheet("color: green;")
        else:
            self.sync_labels['status'].setText("SYNCING")
            self.sync_labels['status'].setStyleSheet("color: yellow;")
            
        self.sync_labels['offset'].setText(f"{status['offset_ns']:.1f} ns")
        self.sync_labels['frequency'].setText(f"{status['frequency_ppb']:+.1f} ppb")
        self.sync_labels['rms'].setText(f"{status['rms_ns']:.1f} ns")
        
    def sync_error(self, error: str):
        self.log_message(f"Synchronization error: {error}", "ERROR")
        QMessageBox.critical(self, "Sync Error", f"Synchronization error: {error}")
        self.toggle_sync()  # Stop sync on error
        
    def run_quick_setup(self):
        reply = QMessageBox.question(
            self, "Quick Setup",
            "This will configure basic TimeNIC settings. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.log_message("Running quick setup...")
            
            # Enable PPS output
            if self.manager.enable_pps_output():
                self.log_message("✓ PPS output enabled", "SUCCESS")
                self.update_indicator('pps_output', True)
            
            # Enable PPS input
            if self.manager.enable_pps_input():
                self.log_message("✓ PPS input enabled", "SUCCESS")
                self.update_indicator('pps_input', True)
                
            self.log_message("Quick setup completed")
            QMessageBox.information(self, "Success", "Quick setup completed successfully!")
            
    def apply_config(self):
        interface = self.interface_combo.currentText()
        ptp_device = self.ptp_device_combo.currentText()
        
        self.manager = TimeNICManager(interface, ptp_device)
        self.log_message(f"Configuration applied: {interface} → {ptp_device}")
        self.refresh_status()
        
    def install_driver(self):
        reply = QMessageBox.question(
            self, "Install Driver",
            "Driver installation requires root privileges and system reboot.\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Check if running as root
            if os.geteuid() != 0:
                QMessageBox.critical(
                    self, "Error",
                    "Please run the application with sudo for driver installation"
                )
                return
                
            self.log_message("Installing patched driver...")
            if self.manager.install_driver():
                self.log_message("Driver installed successfully", "SUCCESS")
                QMessageBox.information(
                    self, "Success",
                    "Driver installed successfully!\nPlease reboot your system."
                )
            else:
                self.log_message("Driver installation failed", "ERROR")
                QMessageBox.critical(self, "Error", "Driver installation failed")
                
    def export_config(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Configuration", "", "JSON Files (*.json)"
        )
        
        if filename:
            config = {
                "interface": self.manager.interface,
                "ptp_device": self.manager.ptp_device,
                "status": self.manager.get_status()
            }
            
            try:
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                self.log_message(f"Configuration exported to {filename}", "SUCCESS")
                QMessageBox.information(self, "Success", "Configuration exported successfully")
            except Exception as e:
                self.log_message(f"Export failed: {e}", "ERROR")
                QMessageBox.critical(self, "Error", f"Export failed: {e}")
                
    def import_config(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration", "", "JSON Files (*.json)"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    config = json.load(f)
                    
                self.interface_combo.setCurrentText(config.get("interface", "enp3s0"))
                self.ptp_device_combo.setCurrentText(config.get("ptp_device", "/dev/ptp0"))
                self.apply_config()
                
                self.log_message(f"Configuration imported from {filename}", "SUCCESS")
                QMessageBox.information(self, "Success", "Configuration imported successfully")
            except Exception as e:
                self.log_message(f"Import failed: {e}", "ERROR")
                QMessageBox.critical(self, "Error", f"Import failed: {e}")
                
    def save_logs(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Logs", "", "Text Files (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_display.toPlainText())
                self.log_message(f"Logs saved to {filename}", "SUCCESS")
                QMessageBox.information(self, "Success", "Logs saved successfully")
            except Exception as e:
                self.log_message(f"Save failed: {e}", "ERROR")
                QMessageBox.critical(self, "Error", f"Save failed: {e}")
                
    def closeEvent(self, event):
        if self.sync_thread and self.sync_thread.isRunning():
            self.sync_thread.stop()
            self.sync_thread.wait()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TimeNIC Manager")
    
    # Set application style
    app.setStyle("Fusion")
    
    window = TimeNICGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()