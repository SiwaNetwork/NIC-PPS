"""
Flask веб-приложение для конфигурации и мониторинга Intel NIC
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import threading

# Добавляем путь к core модулю
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.nic_manager import IntelNICManager, PPSMode, NICInfo
from core.timenic_manager import TimeNICManager, TimeNICInfo, PTPInfo, PTMStatus

app = Flask(__name__)
app.config['SECRET_KEY'] = 'intel-nic-pps-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Глобальные менеджеры
nic_manager = IntelNICManager()
timenic_manager = TimeNICManager()

# Данные мониторинга
monitoring_data = {}
timenic_monitoring_data = {}
monitoring_active = False


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/nics')
def get_nics():
    """API для получения списка NIC карт"""
    try:
        nics = nic_manager.get_all_nics()
        data = []
        
        for nic in nics:
            # Получаем дополнительную информацию
            stats = nic_manager.get_statistics(nic.name)
            temp = nic_manager.get_temperature(nic.name)
            
            data.append({
                'name': nic.name,
                'mac_address': nic.mac_address,
                'ip_address': nic.ip_address,
                'status': nic.status,
                'speed': nic.speed,
                'duplex': nic.duplex,
                'pps_mode': nic.pps_mode.value,
                'tcxo_enabled': nic.tcxo_enabled,
                'temperature': temp,
                'stats': stats
            })
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics')
def get_timenics():
    """API для получения списка TimeNIC карт"""
    try:
        timenics = timenic_manager.get_all_timenics()
        data = []
        
        for timenic in timenics:
            # Получаем дополнительную информацию
            stats = timenic_manager.get_statistics(timenic.name)
            
            data.append({
                'name': timenic.name,
                'mac_address': timenic.mac_address,
                'ip_address': timenic.ip_address,
                'status': timenic.status,
                'pps_mode': timenic.pps_mode.value,
                'tcxo_enabled': timenic.tcxo_enabled,
                'ptm_status': timenic.ptm_status.value,
                'sma1_status': timenic.sma1_status,
                'sma2_status': timenic.sma2_status,
                'phc_offset': timenic.phc_offset,
                'phc_frequency': timenic.phc_frequency,
                'temperature': timenic.temperature,
                'stats': stats
            })
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics/<interface>')
def get_timenic_info(interface):
    """API для получения информации о конкретной TimeNIC карте"""
    try:
        timenic = timenic_manager.get_timenic_by_name(interface)
        if not timenic:
            return jsonify({'success': False, 'error': 'TimeNIC карта не найдена'})
        
        stats = timenic_manager.get_statistics(interface)
        
        data = {
            'name': timenic.name,
            'mac_address': timenic.mac_address,
            'ip_address': timenic.ip_address,
            'status': timenic.status,
            'pps_mode': timenic.pps_mode.value,
            'tcxo_enabled': timenic.tcxo_enabled,
            'ptm_status': timenic.ptm_status.value,
            'sma1_status': timenic.sma1_status,
            'sma2_status': timenic.sma2_status,
            'phc_offset': timenic.phc_offset,
            'phc_frequency': timenic.phc_frequency,
            'temperature': timenic.temperature,
            'stats': stats
        }
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics/<interface>/pps', methods=['POST'])
def set_timenic_pps_mode(interface):
    """API для установки режима PPS для TimeNIC"""
    try:
        data = request.get_json()
        pps_mode = data.get('pps_mode')
        
        if not pps_mode:
            return jsonify({'success': False, 'error': 'Не указан режим PPS'})
        
        from core.timenic_manager import PPSMode
        success = timenic_manager.set_pps_mode(interface, PPSMode(pps_mode))
        
        if success:
            return jsonify({'success': True, 'message': f'PPS режим {pps_mode} установлен для {interface}'})
        else:
            return jsonify({'success': False, 'error': f'Не удалось установить PPS режим для {interface}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics/<interface>/tcxo', methods=['POST'])
def set_timenic_tcxo(interface):
    """API для управления TCXO для TimeNIC"""
    try:
        data = request.get_json()
        enabled = data.get('enabled')
        
        if enabled is None:
            return jsonify({'success': False, 'error': 'Не указан статус TCXO'})
        
        success = timenic_manager.set_tcxo_enabled(interface, enabled)
        
        if success:
            return jsonify({'success': True, 'message': f'TCXO {"включен" if enabled else "выключен"} для {interface}'})
        else:
            return jsonify({'success': False, 'error': f'Не удалось настроить TCXO для {interface}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics/<interface>/ptm', methods=['POST'])
def set_timenic_ptm(interface):
    """API для управления PTM для TimeNIC"""
    try:
        data = request.get_json()
        enabled = data.get('enabled')
        
        if enabled is None:
            return jsonify({'success': False, 'error': 'Не указан статус PTM'})
        
        if enabled:
            success = timenic_manager.enable_ptm(interface)
        else:
            success = timenic_manager.disable_ptm(interface)
        
        if success:
            return jsonify({'success': True, 'message': f'PTM {"включен" if enabled else "выключен"} для {interface}'})
        else:
            return jsonify({'success': False, 'error': f'Не удалось настроить PTM для {interface}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics/<interface>/phc-sync', methods=['POST'])
def start_timenic_phc_sync(interface):
    """API для запуска синхронизации PHC для TimeNIC"""
    try:
        success = timenic_manager.start_phc_synchronization(interface)
        
        if success:
            return jsonify({'success': True, 'message': f'Синхронизация PHC запущена для {interface}'})
        else:
            return jsonify({'success': False, 'error': f'Не удалось запустить синхронизацию PHC для {interface}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/nics/<interface>')
def get_nic_info(interface):
    """API для получения информации о конкретной NIC карте"""
    try:
        nic = nic_manager.get_nic_by_name(interface)
        if not nic:
            return jsonify({'success': False, 'error': 'NIC карта не найдена'})
        
        stats = nic_manager.get_statistics(interface)
        temp = nic_manager.get_temperature(interface)
        
        data = {
            'name': nic.name,
            'mac_address': nic.mac_address,
            'ip_address': nic.ip_address,
            'status': nic.status,
            'speed': nic.speed,
            'duplex': nic.duplex,
            'pps_mode': nic.pps_mode.value,
            'tcxo_enabled': nic.tcxo_enabled,
            'temperature': temp,
            'stats': stats
        }
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/nics/<interface>/pps', methods=['POST'])
def set_pps_mode(interface):
    """API для установки режима PPS"""
    try:
        data = request.get_json()
        mode = data.get('mode')
        
        if not mode:
            return jsonify({'success': False, 'error': 'Не указан режим PPS'})
        
        # Проверяем существование карты
        nic = nic_manager.get_nic_by_name(interface)
        if not nic:
            return jsonify({'success': False, 'error': 'NIC карта не найдена'})
        
        # Устанавливаем режим
        pps_mode = PPSMode(mode)
        success = nic_manager.set_pps_mode(interface, pps_mode)
        
        if success:
            return jsonify({'success': True, 'message': f'PPS режим изменен на {mode}'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка при изменении PPS режима'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/nics/<interface>/tcxo', methods=['POST'])
def set_tcxo(interface):
    """API для настройки TCXO"""
    try:
        data = request.get_json()
        enabled = data.get('enabled')
        
        if enabled is None:
            return jsonify({'success': False, 'error': 'Не указан статус TCXO'})
        
        # Проверяем существование карты
        nic = nic_manager.get_nic_by_name(interface)
        if not nic:
            return jsonify({'success': False, 'error': 'NIC карта не найдена'})
        
        # Устанавливаем TCXO
        success = nic_manager.set_tcxo_enabled(interface, enabled)
        
        if success:
            status = "включен" if enabled else "отключен"
            return jsonify({'success': True, 'message': f'TCXO {status}'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка при настройке TCXO'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """API для управления конфигурацией"""
    if request.method == 'GET':
        # Возвращаем текущую конфигурацию
        try:
            nics = nic_manager.get_all_nics()
            config_data = []
            
            for nic in nics:
                config_data.append({
                    'interface': nic.name,
                    'pps_mode': nic.pps_mode.value,
                    'tcxo_enabled': nic.tcxo_enabled
                })
            
            return jsonify({'success': True, 'data': config_data})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    elif request.method == 'POST':
        # Применяем конфигурацию
        try:
            data = request.get_json()
            if not isinstance(data, list):
                return jsonify({'success': False, 'error': 'Неверный формат конфигурации'})
            
            results = []
            for nic_config in data:
                interface = nic_config.get('interface')
                if not interface:
                    continue
                
                # Проверяем существование карты
                nic = nic_manager.get_nic_by_name(interface)
                if not nic:
                    results.append({
                        'interface': interface,
                        'success': False,
                        'error': 'NIC карта не найдена'
                    })
                    continue
                
                # Применяем PPS настройки
                if 'pps_mode' in nic_config:
                    mode = PPSMode(nic_config['pps_mode'])
                    success = nic_manager.set_pps_mode(interface, mode)
                    results.append({
                        'interface': interface,
                        'setting': 'pps_mode',
                        'success': success,
                        'value': mode.value
                    })
                
                # Применяем TCXO настройки
                if 'tcxo_enabled' in nic_config:
                    enabled = nic_config['tcxo_enabled']
                    success = nic_manager.set_tcxo_enabled(interface, enabled)
                    results.append({
                        'interface': interface,
                        'setting': 'tcxo_enabled',
                        'success': success,
                        'value': enabled
                    })
            
            return jsonify({'success': True, 'results': results})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})


@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    """API для запуска мониторинга"""
    global monitoring_active
    
    try:
        data = request.get_json()
        interfaces = data.get('interfaces', [])
        
        if not interfaces:
            return jsonify({'success': False, 'error': 'Не указаны интерфейсы для мониторинга'})
        
        monitoring_active = True
        
        # Запускаем поток мониторинга
        def monitoring_thread():
            global monitoring_data, timenic_monitoring_data
            
            while monitoring_active:
                try:
                    # Мониторинг обычных NIC карт
                    data = {}
                    for interface in interfaces:
                        nic = nic_manager.get_nic_by_name(interface)
                        if nic:
                            stats = nic_manager.get_statistics(interface)
                            temp = nic_manager.get_temperature(interface)
                            data[interface] = {
                                'stats': stats,
                                'temperature': temp,
                                'status': nic.status,
                                'timestamp': datetime.now().isoformat()
                            }
                    
                    monitoring_data = data
                    
                    # Мониторинг TimeNIC карт
                    timenic_data = {}
                    timenics = timenic_manager.get_all_timenics()
                    for timenic in timenics:
                        stats = timenic_manager.get_statistics(timenic.name)
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
                            'phc_frequency': timenic.phc_frequency,
                            'timestamp': datetime.now().isoformat()
                        }
                    
                    timenic_monitoring_data = timenic_data
                    
                    # Отправляем обновления через WebSocket
                    socketio.emit('monitoring_data', {
                        'nics': data,
                        'timenics': timenic_data
                    })
                    time.sleep(1)  # Обновление каждую секунду
                except Exception as e:
                    print(f"Ошибка в потоке мониторинга: {e}")
        
        thread = threading.Thread(target=monitoring_thread, daemon=True)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Мониторинг запущен'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """API для остановки мониторинга"""
    global monitoring_active
    monitoring_active = False
    return jsonify({'success': True, 'message': 'Мониторинг остановлен'})


@socketio.on('connect')
def handle_connect():
    """Обработчик подключения WebSocket"""
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    """Обработчик отключения WebSocket"""
    print('Client disconnected')


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)