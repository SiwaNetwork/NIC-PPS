"""
flask веб-приложение для конфигурации и мониторинга SHIWA NIC
Версия 1.1.0 - Исправлено определение PTP устройства для Intel I210
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import subprocess
import threading

# Добавляем путь к core модулю
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.nic_manager import IntelNICManager, PPSMode, NICInfo
from core.timenic_manager import TimeNICManager, TimeNICInfo, PTPInfo, PTMStatus
from monitoring import init_flask_metrics, metrics_collector, health_checker

def get_network_statistics(interface):
    """Получает статистику сети для любого интерфейса"""
    try:
        with open('/proc/net/dev', 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            if interface in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    stats = parts[1].split()
                    if len(stats) >= 16:
                        return {
                            'rx_bytes': int(stats[0]),
                            'rx_packets': int(stats[1]),
                            'rx_errors': int(stats[2]),
                            'rx_dropped': int(stats[3]),
                            'tx_bytes': int(stats[8]),
                            'tx_packets': int(stats[9]),
                            'tx_errors': int(stats[10]),
                            'tx_dropped': int(stats[11])
                        }
        
        return {
            'rx_bytes': 0,
            'rx_packets': 0,
            'rx_errors': 0,
            'rx_dropped': 0,
            'tx_bytes': 0,
            'tx_packets': 0,
            'tx_errors': 0,
            'tx_dropped': 0
        }
    except Exception as e:
        print(f"Ошибка получения статистики для {interface}: {e}")
        return {
            'rx_bytes': 0,
            'rx_packets': 0,
            'rx_errors': 0,
            'rx_dropped': 0,
            'tx_bytes': 0,
            'tx_packets': 0,
            'tx_errors': 0,
            'tx_dropped': 0
        }

# Импорт версии
try:
    from version import get_version, get_version_info
except ImportError:
    def get_version():
        return "unknown"
    def get_version_info():
        return {"version": "unknown"}

app = Flask(__name__)
# Конфигурация из окружения
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me')

# Настройка CORS для HTTP и Socket.IO из переменной окружения
cors_env = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
cors_allowed_origins = [origin.strip() for origin in cors_env.split(',') if origin.strip()]
CORS(app, resources={r"/api/*": {"origins": cors_allowed_origins}})
socketio = SocketIO(app, cors_allowed_origins=cors_allowed_origins)

# Глобальные менеджеры
nic_manager = IntelNICManager()
timenic_manager = TimeNICManager()

# Данные мониторинга
monitoring_data = {}
timenic_monitoring_data = {}
monitoring_active = False

# Кэш для оптимизации
nic_cache = {}
timenic_cache = {}
last_timenic_refresh = 0
CACHE_DURATION = 5  # секунд
TIMENIC_REFRESH_INTERVAL = 10  # секунд
MONITORING_INTERVAL = int(os.environ.get('MONITORING_INTERVAL_SEC', '3'))

# Глобальные переменные для синхронизации
phc_sync_process = None
ts2phc_sync_process = None


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/version')
def get_version_api():
    """API для получения версии приложения"""
    try:
        version_info = get_version_info()
        return jsonify({
            "success": True,
            "version": version_info
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/nics')
def get_nics():
    """API для получения списка NIC карт"""
    try:
        nics = nic_manager.get_all_nics()
        data = []
        current_time = time.time()
        
        for nic in nics:
            # Проверяем кэш для статистики
            cache_key = f"{nic.name}_api_stats"
            if cache_key in nic_cache and (current_time - nic_cache[cache_key]['timestamp']) < CACHE_DURATION:
                cached_data = nic_cache[cache_key]['data']
                stats = cached_data['stats']
            else:
                # Получаем дополнительную информацию
                stats = nic_manager.get_statistics(nic.name)
                # Кэшируем данные
                nic_cache[cache_key] = {
                    'data': {'stats': stats},
                    'timestamp': current_time
                }
            
            data.append({
                'name': nic.name,
                'mac_address': nic.mac_address,
                'ip_address': nic.ip_address,
                'status': nic.status,
                'speed': nic.speed,
                'duplex': nic.duplex,
                'pps_mode': nic.pps_mode.value,
                'tcxo_enabled': nic.tcxo_enabled,
                'stats': stats
            })
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics')
def get_timenics():
    """API для получения списка TimeNIC карт"""
    try:
        # Обновляем список устройств перед возвратом
        timenic_manager.refresh()
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
                'speed': timenic.speed,
                'duplex': timenic.duplex,
                'pps_mode': timenic.pps_mode.value,
                'tcxo_enabled': timenic.tcxo_enabled,
                'ptp_info': {
                    'phc_index': timenic.ptp_info.phc_index,
                    'clock_id': timenic.ptp_info.clock_id,
                    'max_adj': timenic.ptp_info.max_adj,
                    'num_alarms': timenic.ptp_info.num_alarms,
                    'num_external_timestamps': timenic.ptp_info.num_external_timestamps,
                    'num_periodic_outputs': timenic.ptp_info.num_periodic_outputs,
                    'num_programmable_pins': timenic.ptp_info.num_programmable_pins,
                    'pps_capabilities': timenic.ptp_info.pps_capabilities
                },
                'ptm_status': timenic.ptm_status.value,
                'stats': stats
            })
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics/<interface>')
def get_timenic_info(interface):
    """API для получения детальной информации о TimeNIC"""
    try:
        timenic = timenic_manager.get_timenic_info(interface)
        if not timenic:
            return jsonify({'success': False, 'error': 'TimeNIC не найден'})
        
        stats = timenic_manager.get_statistics(interface)
        
        data = {
            'name': timenic.name,
            'mac_address': timenic.mac_address,
            'ip_address': timenic.ip_address,
            'status': timenic.status,
            'speed': timenic.speed,
            'duplex': timenic.duplex,
            'pps_mode': timenic.pps_mode.value,
            'tcxo_enabled': timenic.tcxo_enabled,
            'ptp_info': {
                'phc_index': timenic.ptp_info.phc_index,
                'clock_id': timenic.ptp_info.clock_id,
                'max_adj': timenic.ptp_info.max_adj,
                'num_alarms': timenic.ptp_info.num_alarms,
                'num_external_timestamps': timenic.ptp_info.num_external_timestamps,
                'num_periodic_outputs': timenic.ptp_info.num_periodic_outputs,
                'num_programmable_pins': timenic.ptp_info.num_programmable_pins,
                'pps_capabilities': timenic.ptp_info.pps_capabilities
            },
            'ptm_status': timenic.ptm_status.value,
            'stats': stats
        }
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics/<interface>/pps', methods=['POST'])
def set_timenic_pps_mode(interface):
    """API для установки PPS режима TimeNIC"""
    try:
        data = request.get_json()
        mode = data.get('mode')
        
        if mode not in ['disabled', 'input', 'output', 'both']:
            return jsonify({'success': False, 'error': 'Неверный режим PPS'})
        
        success = timenic_manager.set_pps_mode(interface, PPSMode(mode))
        if success:
            # Обновляем информацию о карте
            timenic_manager.refresh()
            return jsonify({'success': True, 'message': f'PPS режим установлен: {mode}'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось установить PPS режим'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics/<interface>/tcxo', methods=['POST'])
def set_timenic_tcxo(interface):
    """API для управления TCXO TimeNIC"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        success = timenic_manager.set_tcxo_enabled(interface, enabled)
        if success:
            return jsonify({'success': True, 'message': f'TCXO {"включен" if enabled else "выключен"}'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось изменить состояние TCXO'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics/<interface>/ptm', methods=['POST'])
def set_timenic_ptm(interface):
    """API для управления PTM TimeNIC"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        master = data.get('master', False)
        
        success = timenic_manager.set_ptm(interface, enabled, master)
        if success:
            return jsonify({'success': True, 'message': f'PTM {"включен" if enabled else "выключен"}'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось изменить состояние PTM'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/timenics/<interface>/phc-sync', methods=['POST'])
def start_timenic_phc_sync(interface):
    """API для запуска PHC синхронизации TimeNIC"""
    try:
        data = request.get_json()
        target_ptp = data.get('target_ptp')
        
        success = timenic_manager.start_phc_sync(interface, target_ptp)
        if success:
            return jsonify({'success': True, 'message': 'PHC синхронизация запущена'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось запустить PHC синхронизацию'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/nics/<interface>')
def get_nic_info(interface):
    """API для получения детальной информации о NIC"""
    try:
        nic = nic_manager.get_nic_info(interface)
        if not nic:
            return jsonify({'success': False, 'error': 'NIC не найден'})
        
        stats = nic_manager.get_statistics(interface)
        
        data = {
            'name': nic.name,
            'mac_address': nic.mac_address,
            'ip_address': nic.ip_address,
            'status': nic.status,
            'speed': nic.speed,
            'duplex': nic.duplex,
            'pps_mode': nic.pps_mode.value,
            'tcxo_enabled': nic.tcxo_enabled,
            'stats': stats
        }
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/nics/<interface>/pps', methods=['POST'])
def set_pps_mode(interface):
    """API для установки PPS режима NIC"""
    try:
        data = request.get_json()
        mode = data.get('mode')
        
        if mode not in ['disabled', 'input', 'output', 'both']:
            return jsonify({'success': False, 'error': 'Неверный режим PPS'})
        
        # Получаем текущий режим для метрик
        current_nic = nic_manager.get_nic_by_name(interface)
        current_mode = current_nic.pps_mode.value if current_nic else 'unknown'
        
        success = nic_manager.set_pps_mode(interface, PPSMode(mode))
        
        # Записываем изменение режима в метрики
        if success:
            metrics_collector.record_pps_mode_change(interface, current_mode, mode)
        print(f"Результат set_pps_mode: {success}")
        
        if success:
            # Обновляем информацию о карте
            nic_manager.refresh_nic_info(interface)
            return jsonify({'success': True, 'message': f'PPS режим установлен: {mode}'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось установить PPS режим'})
    except Exception as e:
        print(f"Исключение в API set_pps_mode: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/nics/<interface>/tcxo', methods=['POST'])
def set_tcxo(interface):
    """API для управления TCXO NIC"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        success = nic_manager.set_tcxo_enabled(interface, enabled)
        if success:
            return jsonify({'success': True, 'message': f'TCXO {"включен" if enabled else "выключен"}'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось изменить состояние TCXO'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/sync/phc/start', methods=['POST'])
def start_phc_sync():
    """API для запуска PHC2SYS синхронизации"""
    global phc_sync_process
    try:
        data = request.get_json()
        source_ptp = data.get('source_ptp')
        target_ptp = data.get('target_ptp')
        
        if not source_ptp or not target_ptp:
            return jsonify({'success': False, 'error': 'Необходимо указать source_ptp и target_ptp'})
        
        success = nic_manager.start_phc_sync(source_ptp, target_ptp)
        if success:
            return jsonify({'success': True, 'message': f'PHC синхронизация запущена: {source_ptp} -> {target_ptp}'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось запустить PHC синхронизацию'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/sync/phc/stop', methods=['POST'])
def stop_phc_sync():
    """API для остановки PHC2SYS синхронизации"""
    global phc_sync_process
    try:
        success = nic_manager.stop_phc_sync()
        if success:
            return jsonify({'success': True, 'message': 'PHC синхронизация остановлена'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось остановить PHC синхронизацию'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/sync/ts2phc/start', methods=['POST'])
def start_ts2phc_sync():
    """API для запуска TS2PHC синхронизации"""
    global ts2phc_sync_process
    try:
        data = request.get_json()
        source_ptp = data.get('source_ptp')
        target_ptp = data.get('target_ptp')
        
        if not source_ptp or not target_ptp:
            return jsonify({'success': False, 'error': 'Необходимо указать source_ptp и target_ptp'})
        
        success = nic_manager.start_ts2phc_sync(source_ptp, target_ptp)
        if success:
            return jsonify({'success': True, 'message': f'TS2PHC синхронизация запущена: {source_ptp} -> {target_ptp}'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось запустить TS2PHC синхронизацию'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/sync/ts2phc/stop', methods=['POST'])
def stop_ts2phc_sync():
    """API для остановки TS2PHC синхронизации"""
    global ts2phc_sync_process
    try:
        success = nic_manager.stop_ts2phc_sync()
        if success:
            return jsonify({'success': True, 'message': 'TS2PHC синхронизация остановлена'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось остановить TS2PHC синхронизацию'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/sync/status')
def get_sync_status():
    """API для получения статуса синхронизации"""
    try:
        status = nic_manager.get_sync_status()
        return jsonify({'success': True, 'data': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """API для управления конфигурацией"""
    if request.method == 'GET':
        try:
            # Получаем текущую конфигурацию
            config = {
                'nics': [],
                'timenics': []
            }
            
            # Конфигурация обычных NIC
            nics = nic_manager.get_all_nics()
            for nic in nics:
                config['nics'].append({
                    'name': nic.name,
                    'pps_mode': nic.pps_mode.value,
                    'tcxo_enabled': nic.tcxo_enabled
                })
            
            # Конфигурация TimeNIC
            timenics = timenic_manager.get_all_timenics()
            for timenic in timenics:
                config['timenics'].append({
                    'name': timenic.name,
                    'pps_mode': timenic.pps_mode.value,
                    'tcxo_enabled': timenic.tcxo_enabled,
                    'ptm_enabled': timenic.ptm_status.enabled,
                    'ptm_master': timenic.ptm_status.master
                })
            
            return jsonify({'success': True, 'data': config})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            # Применяем конфигурацию к обычным NIC
            for nic_config in data.get('nics', []):
                name = nic_config['name']
                pps_mode = PPSMode(nic_config['pps_mode'])
                tcxo_enabled = nic_config['tcxo_enabled']
                
                nic_manager.set_pps_mode(name, pps_mode)
                nic_manager.set_tcxo(name, tcxo_enabled)
            
            # Применяем конфигурацию к TimeNIC
            for timenic_config in data.get('timenics', []):
                name = timenic_config['name']
                pps_mode = PPSMode(timenic_config['pps_mode'])
                tcxo_enabled = timenic_config['tcxo_enabled']
                ptm_enabled = timenic_config.get('ptm_enabled', False)
                ptm_master = timenic_config.get('ptm_master', False)
                
                timenic_manager.set_pps_mode(name, pps_mode)
                timenic_manager.set_tcxo(name, tcxo_enabled)
                timenic_manager.set_ptm(name, ptm_enabled, ptm_master)
            
            return jsonify({'success': True, 'message': 'Конфигурация применена'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})


@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    """API для запуска мониторинга"""
    global monitoring_active
    
    if monitoring_active:
        return jsonify({'success': False, 'error': 'Мониторинг уже запущен'})
    
    try:
        data = request.get_json()
        interface = data.get('interface')
        
        if not interface:
            return jsonify({'success': False, 'error': 'Необходимо указать интерфейс'})
        
        monitoring_active = True
        
        def monitoring_thread():
            global monitoring_active, monitoring_data
            while monitoring_active:
                try:
                    # Получаем статистику сети
                    stats = get_network_statistics(interface)
                    
                    # Получаем PTP статистику (если доступна)
                    ptp_stats = {}
                    try:
                        ptp_stats = nic_manager.get_ptp_statistics(interface)
                    except:
                        ptp_stats = {'error': 'PTP статистика недоступна'}
                    
                    monitoring_data = {
                        'timestamp': datetime.now().isoformat(),
                        'interface': interface,
                        'stats': stats,
                        'ptp_stats': ptp_stats
                    }
                    
                    # Отправляем данные через WebSocket
                    socketio.emit('monitoring_data', monitoring_data)
                    
                    time.sleep(MONITORING_INTERVAL)
                except Exception as e:
                    print(f"Ошибка мониторинга: {e}")
                    time.sleep(MONITORING_INTERVAL)
        
        thread = threading.Thread(target=monitoring_thread, daemon=True)
        thread.start()
        
        return jsonify({'success': True, 'message': f'Мониторинг запущен для {interface}'})
    except Exception as e:
        monitoring_active = False
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """API для остановки мониторинга"""
    global monitoring_active
    monitoring_active = False
    return jsonify({'success': True, 'message': 'Мониторинг остановлен'})


@app.route('/api/ptp/devices', methods=['GET'])
def get_ptp_devices():
    """API для получения списка доступных PTP устройств"""
    try:
        import glob
        ptp_devices = glob.glob('/dev/ptp*')
        
        # Получаем дополнительную информацию о каждом устройстве
        devices_info = []
        for device in ptp_devices:
            device_info = {
                'path': device,
                'name': device.split('/')[-1],
                'available': True
            }
            
            # Проверяем доступность устройства (без sudo)
            try:
                # Простая проверка существования файла
                if os.path.exists(device):
                    device_info['available'] = True
                    
                    # Пытаемся получить информацию о пинах (с sudo, но не критично)
                    try:
                        result = subprocess.run(['testptp', '-d', device, '-l'], 
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            device_info['pins'] = result.stdout.strip()
                    except Exception:
                        # Если не удалось получить информацию о пинах, это не критично
                        device_info['pins'] = 'Информация недоступна'
                else:
                    device_info['available'] = False
            except Exception:
                device_info['available'] = False
            
            devices_info.append(device_info)
        
        return jsonify({'success': True, 'data': devices_info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/ptp/monitor/<interface>', methods=['GET'])
def get_ptp_monitor(interface):
    """API для получения PTP мониторинга в реальном времени"""
    try:
        # Получаем PTP статистику
        ptp_stats = nic_manager.get_ptp_statistics(interface)
        
        # Получаем информацию о PTP устройствах
        ptp_devices = []
        try:
            import glob
            ptp_devices = glob.glob('/dev/ptp*')
        except Exception:
            pass
        
        # Получаем статус PTP синхронизации
        ptp_sync_status = {
            'phc2sys_running': False,
            'ts2phc_running': False,
            'ptp4l_running': False
        }
        
        try:
            # Проверяем запущенные процессы
            result = subprocess.run(['pgrep', '-f', 'phc2sys'], capture_output=True, text=True)
            ptp_sync_status['phc2sys_running'] = result.returncode == 0
            
            result = subprocess.run(['pgrep', '-f', 'ts2phc'], capture_output=True, text=True)
            ptp_sync_status['ts2phc_running'] = result.returncode == 0
            
            result = subprocess.run(['pgrep', '-f', 'ptp4l'], capture_output=True, text=True)
            ptp_sync_status['ptp4l_running'] = result.returncode == 0
            
            # Также проверяем альтернативные процессы
            result = subprocess.run(['pgrep', '-f', 'phc_sync.sh'], capture_output=True, text=True)
            ptp_sync_status['alternative_sync_running'] = result.returncode == 0
        except Exception:
            pass
        
        data = {
            'interface': interface,
            'ptp_stats': ptp_stats,
            'ptp_devices': ptp_devices,
            'ptp_sync_status': ptp_sync_status,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@socketio.on('connect')
def handle_connect():
    """Обработчик подключения WebSocket"""
    print('Клиент подключился')


@socketio.on('disconnect')
def handle_disconnect():
    """Обработчик отключения WebSocket"""
    print('Клиент отключился')


# Инициализация метрик
init_flask_metrics(app)

# Добавляем endpoint для проверки состояния системы
@app.route('/api/health')
def health_check():
    """API для проверки состояния системы"""
    return jsonify(health_checker.run_all_checks())

@app.route('/api/interfaces/active')
def get_active_interfaces():
    """API для получения списка активных интерфейсов"""
    try:
        import subprocess
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
        interfaces = []
        
        for line in result.stdout.split('\n'):
            if 'state UP' in line and 'LOOPBACK' not in line:
                # Извлекаем имя интерфейса
                parts = line.split(':')
                if len(parts) >= 2:
                    interface_name = parts[1].strip().split('@')[0]
                    if interface_name and interface_name != 'lo':
                        interfaces.append(interface_name)
        
        return jsonify({
            'success': True,
            'interfaces': interfaces
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    debug_enabled = os.environ.get('FLASK_DEBUG', '0') == '1'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    socketio.run(app, host=host, port=port, debug=debug_enabled)