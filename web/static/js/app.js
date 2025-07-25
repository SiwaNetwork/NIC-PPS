// Глобальные переменные
let socket = null;
let trafficChart = null;
let temperatureChart = null;
let monitoringData = {};
let currentMonitoringInterface = null;
let isInitialized = false;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Быстрая инициализация основных элементов
    initializeBasicUI();
    
    // Ленивая инициализация остальных компонентов
    setTimeout(() => {
        initializeSocket();
        refreshNICs();
        refreshTimeNICs();
        loadPtpDevices();
    }, 100);
    
    // Инициализация графиков только при необходимости
    document.addEventListener('click', function(e) {
        if (e.target && e.target.getAttribute('data-bs-target') === '#monitoring') {
            if (!isInitialized) {
                initializeCharts();
                isInitialized = true;
            }
        }
        
        // Автоматическое обновление PTP устройств при переключении на вкладку синхронизации
        if (e.target && e.target.getAttribute('data-bs-target') === '#sync') {
            loadPtpDevices();
        }
    });
    
    // Обработчики событий
    setupEventListeners();
});

// Быстрая инициализация UI
function initializeBasicUI() {
    // Показываем индикатор загрузки
    const loadingElements = document.querySelectorAll('.loading-indicator');
    loadingElements.forEach(el => {
        el.style.display = 'block';
    });
    
    // Обновляем статус соединения
    updateConnectionStatus(false);
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Используем делегирование событий для лучшей производительности
    document.addEventListener('change', function(e) {
        if (e.target.id === 'nicSelect') {
            onNicSelectChange();
        } else if (e.target.id === 'monitorNicSelect') {
            onMonitorNicSelectChange();
        } else if (e.target.id === 'configFile') {
            onConfigFileChange(e);
        }
    });
    
    // Обработчики для кнопок
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-refresh')) {
            e.preventDefault();
            refreshNICs();
        }
});
}

// Инициализация WebSocket соединения
function initializeSocket() {
    try {
        socket = io({
            timeout: 5000,
            reconnection: true,
            reconnectionDelay: 1000
        });
    
    socket.on('connect', function() {
        updateConnectionStatus(true);
    });
    
    socket.on('disconnect', function() {
        updateConnectionStatus(false);
    });
    
    socket.on('monitoring_data', function(data) {
        updateMonitoringData(data);
    });
        
        socket.on('connect_error', function() {
            console.log('WebSocket connection error');
            updateConnectionStatus(false);
        });
    } catch (error) {
        console.error('WebSocket initialization error:', error);
        updateConnectionStatus(false);
    }
}

// Обновление статуса соединения
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
    if (connected) {
        statusElement.innerHTML = '<i class="fas fa-circle text-success"></i> Подключено';
    } else {
            statusElement.innerHTML = '<i class="fas fa-circle text-warning"></i> Отключено';
        }
    }
}

// Обновление списка NIC карт с кэшированием
let nicCache = {};
let lastNicRefresh = 0;
const NIC_CACHE_DURATION = 5000; // 5 секунд

function refreshNICs() {
    const now = Date.now();
    
    // Проверяем кэш
    if (nicCache.data && (now - lastNicRefresh) < NIC_CACHE_DURATION) {
        updateNICTable(nicCache.data);
        updateNICSelects(nicCache.data);
        return;
    }
    
    // Показываем индикатор загрузки
    showLoadingIndicator('nicTableBody');
    
    fetch('/api/nics')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Кэшируем данные
                nicCache.data = data.data;
                lastNicRefresh = now;
                
                updateNICTable(data.data);
                updateNICSelects(data.data);
                hideLoadingIndicator('nicTableBody');
            } else {
                showAlert('Ошибка', 'Не удалось загрузить список NIC карт: ' + data.error);
                hideLoadingIndicator('nicTableBody');
            }
        })
        .catch(error => {
            console.error('Error loading NICs:', error);
            showAlert('Ошибка', 'Ошибка сети: ' + error.message);
            hideLoadingIndicator('nicTableBody');
        });
}

// Показать индикатор загрузки
function showLoadingIndicator(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <tr>
                <td colspan="9" class="text-center">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Загрузка...</span>
                    </div>
                    Загрузка...
                </td>
            </tr>
        `;
    }
}

// Скрыть индикатор загрузки
function hideLoadingIndicator(elementId) {
    const element = document.getElementById(elementId);
    if (element && element.querySelector('.spinner-border')) {
        // Индикатор будет заменен данными
    }
}

// Обновление таблицы NIC карт с оптимизацией
function updateNICTable(nics) {
    const tbody = document.getElementById('nicTableBody');
    if (!tbody) return;
    
    // Используем DocumentFragment для оптимизации
    const fragment = document.createDocumentFragment();
    
    if (nics.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="9" class="text-center text-muted">NIC карты не обнаружены</td>';
        fragment.appendChild(row);
    } else {
    nics.forEach(nic => {
        const row = document.createElement('tr');
        row.innerHTML = `
                <td><strong>${escapeHtml(nic.name)}</strong></td>
                <td><code>${escapeHtml(nic.mac_address)}</code></td>
                <td>${escapeHtml(nic.ip_address || 'N/A')}</td>
                <td><span class="badge ${nic.status === 'up' ? 'bg-success' : 'bg-danger'}">${escapeHtml(nic.status)}</span></td>
                <td>${escapeHtml(nic.speed)}</td>
                <td><span class="badge bg-info">${escapeHtml(nic.pps_mode)}</span></td>
            <td><i class="fas fa-${nic.tcxo_enabled ? 'check text-success' : 'times text-danger'}"></i></td>
            <td>${nic.temperature ? nic.temperature.toFixed(1) + '°C' : 'N/A'}</td>
            <td>
                <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary btn-sm" onclick="configureNIC('${escapeHtml(nic.name)}')">
                        <i class="fas fa-cog"></i>
                    </button>
                        <button class="btn btn-outline-info btn-sm" onclick="showNICInfo('${escapeHtml(nic.name)}')">
                        <i class="fas fa-info"></i>
                    </button>
                </div>
            </td>
        `;
            fragment.appendChild(row);
    });
    }
    
    tbody.innerHTML = '';
    tbody.appendChild(fragment);
}

// Экранирование HTML для безопасности
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Обновление селектов NIC с оптимизацией
function updateNICSelects(nics) {
    const nicSelect = document.getElementById('nicSelect');
    const monitorNicSelect = document.getElementById('monitorNicSelect');
    const ptpMonitorNicSelect = document.getElementById('ptpMonitorNicSelect');
    
    if (nicSelect) {
        nicSelect.innerHTML = '<option value="">Выберите NIC</option>';
        nics.forEach(nic => {
            const option = document.createElement('option');
            option.value = nic.name;
            option.textContent = `${nic.name} (${nic.mac_address})`;
            nicSelect.appendChild(option);
        });
    }
    
    if (monitorNicSelect) {
        monitorNicSelect.innerHTML = '<option value="">Выберите NIC для мониторинга</option>';
        nics.forEach(nic => {
            const option = document.createElement('option');
            option.value = nic.name;
            option.textContent = `${nic.name} (${nic.mac_address})`;
            monitorNicSelect.appendChild(option);
        });
    }
    
    if (ptpMonitorNicSelect) {
        ptpMonitorNicSelect.innerHTML = '<option value="">Выберите NIC для PTP мониторинга</option>';
        nics.forEach(nic => {
            const option = document.createElement('option');
            option.value = nic.name;
            option.textContent = `${nic.name} (${nic.mac_address})`;
            ptpMonitorNicSelect.appendChild(option);
        });
    }
}

// Обработчик изменения выбранной NIC карты
function onNicSelectChange() {
    const nicName = document.getElementById('nicSelect').value;
    if (nicName) {
        loadNICInfo(nicName);
    } else {
        document.getElementById('nicInfo').innerHTML = '<p class="text-muted">Выберите NIC карту для просмотра информации</p>';
    }
}

// Обработчик изменения выбранной NIC для мониторинга
function onMonitorNicSelectChange() {
    const nicName = document.getElementById('monitorNicSelect').value;
    if (nicName) {
        currentMonitoringInterface = nicName;
        updateCharts();
    }
}

// Загрузка информации о NIC карте
function loadNICInfo(nicName) {
    fetch(`/api/nics/${nicName}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayNICInfo(data.data);
                updateConfigForm(data.data);
            } else {
                showAlert('Ошибка', 'Не удалось загрузить информацию о карте: ' + data.error);
            }
        })
        .catch(error => {
            showAlert('Ошибка', 'Ошибка сети: ' + error.message);
        });
}

// Отображение информации о NIC карте
function displayNICInfo(nic) {
    const infoDiv = document.getElementById('nicInfo');
    infoDiv.innerHTML = `
        <div class="row">
            <div class="col-6">
                <strong>Имя:</strong><br>
                <strong>MAC адрес:</strong><br>
                <strong>IP адрес:</strong><br>
                <strong>Статус:</strong><br>
                <strong>Скорость:</strong><br>
                <strong>Дуплекс:</strong><br>
            </div>
            <div class="col-6">
                ${nic.name}<br>
                <code>${nic.mac_address}</code><br>
                ${nic.ip_address || 'N/A'}<br>
                <span class="badge ${nic.status === 'up' ? 'bg-success' : 'bg-danger'}">${nic.status}</span><br>
                ${nic.speed}<br>
                ${nic.duplex}<br>
            </div>
        </div>
        <hr>
        <div class="row">
            <div class="col-6">
                <strong>PPS режим:</strong><br>
                <strong>TCXO:</strong><br>
                <strong>Температура:</strong><br>
            </div>
            <div class="col-6">
                <span class="badge bg-info">${nic.pps_mode}</span><br>
                <i class="fas fa-${nic.tcxo_enabled ? 'check text-success' : 'times text-danger'}"></i><br>
                ${nic.temperature ? nic.temperature.toFixed(1) + '°C' : 'N/A'}<br>
            </div>
        </div>
    `;
}

// Обновление формы конфигурации
function updateConfigForm(nic) {
    document.getElementById('ppsMode').value = nic.pps_mode;
    document.getElementById('tcxoEnabled').checked = nic.tcxo_enabled;
}

// Применение настроек PPS
function applyPPS() {
    const nicName = document.getElementById('nicSelect').value;
    const mode = document.getElementById('ppsMode').value;
    
    if (!nicName) {
        showAlert('Ошибка', 'Выберите NIC карту');
        return;
    }
    
    fetch(`/api/nics/${nicName}/pps`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode: mode })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успех', data.message);
            refreshNICs();
        } else {
            showAlert('Ошибка', data.error);
        }
    })
    .catch(error => {
        showAlert('Ошибка', 'Ошибка сети: ' + error.message);
    });
}

// Применение настроек TCXO
function applyTCXO() {
    const nicName = document.getElementById('nicSelect').value;
    const enabled = document.getElementById('tcxoEnabled').checked;
    
    if (!nicName) {
        showAlert('Ошибка', 'Выберите NIC карту');
        return;
    }
    
    fetch(`/api/nics/${nicName}/tcxo`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ enabled: enabled })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успех', data.message);
            refreshNICs();
        } else {
            showAlert('Ошибка', data.error);
        }
    })
    .catch(error => {
        showAlert('Ошибка', 'Ошибка сети: ' + error.message);
    });
}

// Сохранение конфигурации
function saveConfig() {
    fetch('/api/config')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'nic_config.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                showAlert('Успех', 'Конфигурация сохранена');
            } else {
                showAlert('Ошибка', data.error);
            }
        })
        .catch(error => {
            showAlert('Ошибка', 'Ошибка сети: ' + error.message);
        });
}

// Загрузка конфигурации
function loadConfig() {
    document.getElementById('configFile').click();
}

// Обработчик выбора файла конфигурации
function onConfigFileChange(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const config = JSON.parse(e.target.result);
            applyConfig(config);
        } catch (error) {
            showAlert('Ошибка', 'Неверный формат файла конфигурации');
        }
    };
    reader.readAsText(file);
    
    // Очищаем input
    event.target.value = '';
}

// Применение конфигурации
function applyConfig(config) {
    fetch('/api/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успех', 'Конфигурация применена');
            refreshNICs();
        } else {
            showAlert('Ошибка', data.error);
        }
    })
    .catch(error => {
        showAlert('Ошибка', 'Ошибка сети: ' + error.message);
    });
}

// Инициализация графиков
function initializeCharts() {
    console.log('Инициализация графиков...');
    
    // График трафика
    const trafficCtx = document.getElementById('trafficChart');
    if (trafficCtx) {
        trafficChart = new Chart(trafficCtx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'RX (байт/с)',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                },
                {
                    label: 'TX (байт/с)',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Байт/с'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Время'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Мониторинг трафика'
                    }
                }
            }
        });
        console.log('График трафика инициализирован');
    } else {
        console.log('Элемент trafficChart не найден');
    }
}

// Запуск мониторинга
function startMonitoring() {
    const nicName = document.getElementById('monitorNicSelect').value;
    if (!nicName) {
        showAlert('Ошибка', 'Выберите NIC карту для мониторинга');
        return;
    }
    
    currentMonitoringInterface = nicName;
    
    fetch('/api/monitoring/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ interface: nicName })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успех', 'Мониторинг запущен');
            // Обновляем кнопки
            const startBtn = document.querySelector('button[onclick="startMonitoring()"]');
            const stopBtn = document.querySelector('button[onclick="stopMonitoring()"]');
            if (startBtn) startBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;
        } else {
            showAlert('Ошибка', data.error);
        }
    })
    .catch(error => {
        showAlert('Ошибка', 'Ошибка сети: ' + error.message);
    });
}

// Остановка мониторинга
function stopMonitoring() {
    fetch('/api/monitoring/stop', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успех', 'Мониторинг остановлен');
            // Обновляем кнопки
            const startBtn = document.querySelector('button[onclick="startMonitoring()"]');
            const stopBtn = document.querySelector('button[onclick="stopMonitoring()"]');
            if (startBtn) startBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
        } else {
            showAlert('Ошибка', data.error);
        }
    })
    .catch(error => {
        showAlert('Ошибка', 'Ошибка сети: ' + error.message);
    });
}

// Обновление данных мониторинга
function updateMonitoringData(data) {
    console.log('Получены данные мониторинга:', data);
    monitoringData = data;
    updateCharts();
    updateStats();
}

// Обновление графиков
function updateCharts() {
    if (!monitoringData || !monitoringData.stats) {
        console.log('Нет данных для обновления графиков');
        return;
    }
    
    const data = monitoringData;
    const timestamp = new Date().toLocaleTimeString();
    
    // Обновляем график трафика
    if (data.stats) {
        const rxSpeed = data.stats.rx_bytes || 0;
        const txSpeed = data.stats.tx_bytes || 0;
        
        if (trafficChart) {
        trafficChart.data.labels.push(timestamp);
        trafficChart.data.datasets[0].data.push(rxSpeed);
        trafficChart.data.datasets[1].data.push(txSpeed);
        
        // Ограничиваем количество точек
        if (trafficChart.data.labels.length > 20) {
            trafficChart.data.labels.shift();
            trafficChart.data.datasets[0].data.shift();
            trafficChart.data.datasets[1].data.shift();
        }
        
        trafficChart.update();
    }
    }
}

// Обновление статистики
function updateStats() {
    if (!monitoringData) {
        return;
    }
    
    const data = monitoringData;
    const statsContainer = document.getElementById('statsContainer');
    
    if (!statsContainer) {
        console.log('Элемент statsContainer не найден');
        return;
    }
    
    let statsHtml = '';
    if (data.stats) {
        statsHtml = `
            <div class="row">
                <div class="col-6">
                    <strong>Принято пакетов:</strong><br>
                    <span class="badge bg-primary">${data.stats.rx_packets || 0}</span><br><br>
                    <strong>Отправлено пакетов:</strong><br>
                    <span class="badge bg-success">${data.stats.tx_packets || 0}</span><br><br>
                    <strong>Ошибки приема:</strong><br>
                    <span class="badge bg-danger">${data.stats.rx_errors || 0}</span><br><br>
                    <strong>Ошибки отправки:</strong><br>
                    <span class="badge bg-warning">${data.stats.tx_errors || 0}</span>
                </div>
                <div class="col-6">
                    <strong>Принято байт:</strong><br>
                    <span class="badge bg-info">${(data.stats.rx_bytes || 0).toLocaleString()}</span><br><br>
                    <strong>Отправлено байт:</strong><br>
                    <span class="badge bg-info">${(data.stats.tx_bytes || 0).toLocaleString()}</span><br><br>
                    <strong>Отброшено при приеме:</strong><br>
                    <span class="badge bg-secondary">${data.stats.rx_dropped || 0}</span><br><br>
                    <strong>Отброшено при отправке:</strong><br>
                    <span class="badge bg-secondary">${data.stats.tx_dropped || 0}</span>
                </div>
            </div>
        `;
        
        // Добавляем PTP статистику если есть
        if (data.ptp_stats) {
            statsHtml += `
                <hr>
                <h6><i class="fas fa-clock"></i> PTP Статистика:</h6>
                <div class="row">
                    <div class="col-6">
                        <strong>PTP RX пакеты:</strong><br>
                        <span class="badge bg-primary">${data.ptp_stats.ptp_rx_packets || 0}</span><br><br>
                        <strong>PTP TX пакеты:</strong><br>
                        <span class="badge bg-success">${data.ptp_stats.ptp_tx_packets || 0}</span><br><br>
                        <strong>PTP Sync пакеты:</strong><br>
                        <span class="badge bg-info">${data.ptp_stats.ptp_sync_packets || 0}</span><br><br>
                        <strong>PTP Delay Req:</strong><br>
                        <span class="badge bg-warning">${data.ptp_stats.ptp_delay_req_packets || 0}</span>
                    </div>
                    <div class="col-6">
                        <strong>PTP Follow Up:</strong><br>
                        <span class="badge bg-secondary">${data.ptp_stats.ptp_follow_up_packets || 0}</span><br><br>
                        <strong>PTP Delay Resp:</strong><br>
                        <span class="badge bg-dark">${data.ptp_stats.ptp_delay_resp_packets || 0}</span><br><br>
                        <strong>PTP Announce:</strong><br>
                        <span class="badge bg-light text-dark">${data.ptp_stats.ptp_announce_packets || 0}</span><br><br>
                        <strong>PTP Master/Slave:</strong><br>
                        <span class="badge bg-danger">${data.ptp_stats.ptp_master_packets || 0}</span> / 
                        <span class="badge bg-info">${data.ptp_stats.ptp_slave_packets || 0}</span>
                    </div>
                </div>
                <div class="row mt-2">
                    <div class="col-12">
                        <small class="text-muted">
                            <i class="fas fa-info-circle"></i> 
                            PTP трафик отслеживается на портах 319 (Event) и 320 (General)
                        </small>
                    </div>
                </div>
            `;
    }
    } else {
        statsHtml = '<p class="text-muted">Нет данных статистики</p>';
    }
    
    statsContainer.innerHTML = statsHtml;
}

// Вспомогательные функции
function configureNIC(nicName) {
    document.getElementById('nicSelect').value = nicName;
    document.getElementById('nicSelect').dispatchEvent(new Event('change'));
    
    // Переключаемся на вкладку конфигурации
    const configTab = document.getElementById('config-tab');
    const configTabInstance = new bootstrap.Tab(configTab);
    configTabInstance.show();
}

function showNICInfo(nicName) {
    loadNICInfo(nicName);
    
    // Переключаемся на вкладку конфигурации
    const configTab = document.getElementById('config-tab');
    const configTabInstance = new bootstrap.Tab(configTab);
    configTabInstance.show();
}

function showAlert(title, message) {
    document.getElementById('alertModalTitle').textContent = title;
    document.getElementById('alertModalBody').textContent = message;
    const modal = new bootstrap.Modal(document.getElementById('alertModal'));
    modal.show();
}

// ===== TimeNIC функции =====

// Обновление списка TimeNIC карт
function refreshTimeNICs() {
    fetch('/api/timenics')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateTimeNICTable(data.data);
            } else {
                showAlert('Ошибка', 'Не удалось загрузить список TimeNIC карт: ' + data.error);
            }
        })
        .catch(error => {
            showAlert('Ошибка', 'Ошибка сети: ' + error.message);
        });
}

// Обновление таблицы TimeNIC карт
function updateTimeNICTable(timenics) {
    const tbody = document.getElementById('timenicTableBody');
    tbody.innerHTML = '';
    
    if (timenics.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">TimeNIC карты не обнаружены</td></tr>';
        return;
    }
    
    timenics.forEach(timenic => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${timenic.name}</strong></td>
            <td><code>${timenic.mac_address}</code></td>
            <td>${timenic.ip_address || 'N/A'}</td>
            <td><span class="badge ${timenic.status === 'up' ? 'bg-success' : 'bg-danger'}">${timenic.status}</span></td>
            <td><span class="badge bg-info">${timenic.pps_mode}</span></td>
            <td><i class="fas fa-${timenic.tcxo_enabled ? 'check text-success' : 'times text-danger'}"></i></td>
            <td><span class="badge ${timenic.ptm_status === 'enabled' ? 'bg-success' : 'bg-secondary'}">${timenic.ptm_status}</span></td>
            <td><span class="badge ${timenic.sma1_status === 'enabled' ? 'bg-success' : 'bg-secondary'}">${timenic.sma1_status}</span></td>
            <td><span class="badge ${timenic.sma2_status === 'enabled' ? 'bg-success' : 'bg-secondary'}">${timenic.sma2_status}</span></td>
            <td>${timenic.phc_offset || 'N/A'}</td>
            <td>${timenic.temperature ? timenic.temperature.toFixed(1) + '°C' : 'N/A'}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary btn-sm" onclick="configureTimeNIC('${timenic.name}')">
                        <i class="fas fa-cog"></i>
                    </button>
                    <button class="btn btn-outline-info btn-sm" onclick="showTimeNICInfo('${timenic.name}')">
                        <i class="fas fa-info"></i>
                    </button>
                    <button class="btn btn-outline-success btn-sm" onclick="startTimeNICPhcSync('${timenic.name}')">
                        <i class="fas fa-sync"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Настройка TimeNIC карты
function configureTimeNIC(timenicName) {
    // Переключение на вкладку конфигурации
    const configTab = document.getElementById('config-tab');
    const tab = new bootstrap.Tab(configTab);
    tab.show();
    
    // Загрузка информации о TimeNIC
    loadTimeNICInfo(timenicName);
}

// Показать информацию о TimeNIC
function showTimeNICInfo(timenicName) {
    loadTimeNICInfo(timenicName);
}

// Загрузка информации о TimeNIC
function loadTimeNICInfo(timenicName) {
    fetch(`/api/timenics/${timenicName}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayTimeNICInfo(data.data);
            } else {
                showAlert('Ошибка', 'Не удалось загрузить информацию о TimeNIC: ' + data.error);
            }
        })
        .catch(error => {
            showAlert('Ошибка', 'Ошибка сети: ' + error.message);
        });
}

// Отображение информации о TimeNIC
function displayTimeNICInfo(timenic) {
    const infoDiv = document.getElementById('nicInfo');
    infoDiv.innerHTML = `
        <h6>${timenic.name}</h6>
        <table class="table table-sm">
            <tr><td><strong>MAC адрес:</strong></td><td><code>${timenic.mac_address}</code></td></tr>
            <tr><td><strong>IP адрес:</strong></td><td>${timenic.ip_address || 'N/A'}</td></tr>
            <tr><td><strong>Статус:</strong></td><td><span class="badge ${timenic.status === 'up' ? 'bg-success' : 'bg-danger'}">${timenic.status}</span></td></tr>
            <tr><td><strong>PPS режим:</strong></td><td><span class="badge bg-info">${timenic.pps_mode}</span></td></tr>
            <tr><td><strong>TCXO:</strong></td><td><i class="fas fa-${timenic.tcxo_enabled ? 'check text-success' : 'times text-danger'}"></i></td></tr>
            <tr><td><strong>PTM:</strong></td><td><span class="badge ${timenic.ptm_status === 'enabled' ? 'bg-success' : 'bg-secondary'}">${timenic.ptm_status}</span></td></tr>
            <tr><td><strong>SMA1 (SDP0):</strong></td><td><span class="badge ${timenic.sma1_status === 'enabled' ? 'bg-success' : 'bg-secondary'}">${timenic.sma1_status}</span></td></tr>
            <tr><td><strong>SMA2 (SDP1):</strong></td><td><span class="badge ${timenic.sma2_status === 'enabled' ? 'bg-success' : 'bg-secondary'}">${timenic.sma2_status}</span></td></tr>
            <tr><td><strong>PHC Offset:</strong></td><td>${timenic.phc_offset || 'N/A'}</td></tr>
            <tr><td><strong>PHC Frequency:</strong></td><td>${timenic.phc_frequency || 'N/A'}</td></tr>
            <tr><td><strong>Температура:</strong></td><td>${timenic.temperature ? timenic.temperature.toFixed(1) + '°C' : 'N/A'}</td></tr>
        </table>
    `;
}

// Запуск синхронизации PHC для TimeNIC
// PTP Мониторинг
let ptpMonitoringInterval = null;
let currentPtpInterface = null;

function startPtpMonitoring() {
    const interface = document.getElementById('ptpMonitorNicSelect').value;
    if (!interface) {
        showAlert('Ошибка', 'Выберите NIC для PTP мониторинга');
        return;
    }
    
    currentPtpInterface = interface;
    
    // Останавливаем предыдущий мониторинг если есть
    if (ptpMonitoringInterval) {
        clearInterval(ptpMonitoringInterval);
    }
    
    // Запускаем мониторинг
    ptpMonitoringInterval = setInterval(() => {
        fetchPtpData(interface);
    }, 2000); // Обновляем каждые 2 секунды
    
    // Первоначальный запрос
    fetchPtpData(interface);
    
    showAlert('Успех', `PTP мониторинг запущен для ${interface}`);
}

function stopPtpMonitoring() {
    if (ptpMonitoringInterval) {
        clearInterval(ptpMonitoringInterval);
        ptpMonitoringInterval = null;
    }
    currentPtpInterface = null;
    
    // Очищаем отображение
    document.getElementById('ptpStatsContainer').innerHTML = 
        '<p class="text-muted">PTP мониторинг остановлен</p>';
    
    showAlert('Информация', 'PTP мониторинг остановлен');
}

function fetchPtpData(interface) {
    fetch(`/api/ptp/monitor/${interface}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updatePtpStats(data.data);
                updatePtpSyncStatus(data.data.ptp_sync_status);
            } else {
                console.error('Ошибка получения PTP данных:', data.error);
            }
        })
        .catch(error => {
            console.error('Ошибка запроса PTP данных:', error);
        });
}

function updatePtpStats(data) {
    const container = document.getElementById('ptpStatsContainer');
    const ptpStats = data.ptp_stats;
    
    let html = `
        <h6><i class="fas fa-chart-bar"></i> PTP Статистика для ${data.interface}:</h6>
        <div class="row">
            <div class="col-6">
                <strong>PTP RX пакеты:</strong><br>
                <span class="badge bg-primary">${ptpStats.ptp_rx_packets || 0}</span><br><br>
                <strong>PTP TX пакеты:</strong><br>
                <span class="badge bg-success">${ptpStats.ptp_tx_packets || 0}</span><br><br>
                <strong>PTP Sync пакеты:</strong><br>
                <span class="badge bg-info">${ptpStats.ptp_sync_packets || 0}</span><br><br>
                <strong>PTP Delay Req:</strong><br>
                <span class="badge bg-warning">${ptpStats.ptp_delay_req_packets || 0}</span>
            </div>
            <div class="col-6">
                <strong>PTP Follow Up:</strong><br>
                <span class="badge bg-secondary">${ptpStats.ptp_follow_up_packets || 0}</span><br><br>
                <strong>PTP Delay Resp:</strong><br>
                <span class="badge bg-dark">${ptpStats.ptp_delay_resp_packets || 0}</span><br><br>
                <strong>PTP Announce:</strong><br>
                <span class="badge bg-light text-dark">${ptpStats.ptp_announce_packets || 0}</span><br><br>
                <strong>PTP Master/Slave:</strong><br>
                <span class="badge bg-danger">${ptpStats.ptp_master_packets || 0}</span> / 
                <span class="badge bg-info">${ptpStats.ptp_slave_packets || 0}</span>
            </div>
        </div>
        <div class="row mt-2">
            <div class="col-12">
                <small class="text-muted">
                    <i class="fas fa-info-circle"></i> 
                    Обновлено: ${new Date().toLocaleTimeString()}
                </small>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

function updatePtpSyncStatus(syncStatus) {
    // Обновляем статус phc2sys
    const phc2sysElement = document.getElementById('phc2sysStatus');
    if (phc2sysElement) {
        if (syncStatus.phc2sys_running) {
            phc2sysElement.className = 'badge bg-success';
            phc2sysElement.textContent = 'phc2sys: Запущен';
        } else {
            phc2sysElement.className = 'badge bg-danger';
            phc2sysElement.textContent = 'phc2sys: Остановлен';
        }
    }
    
    // Обновляем статус ts2phc
    const ts2phcElement = document.getElementById('ts2phcStatus');
    if (ts2phcElement) {
        if (syncStatus.ts2phc_running) {
            ts2phcElement.className = 'badge bg-success';
            ts2phcElement.textContent = 'ts2phc: Запущен';
        } else {
            ts2phcElement.className = 'badge bg-danger';
            ts2phcElement.textContent = 'ts2phc: Остановлен';
        }
    }
    
    // Обновляем статус ptp4l
    const ptp4lElement = document.getElementById('ptp4lStatus');
    if (ptp4lElement) {
        if (syncStatus.ptp4l_running) {
            ptp4lElement.className = 'badge bg-success';
            ptp4lElement.textContent = 'ptp4l: Запущен';
        } else {
            ptp4lElement.className = 'badge bg-danger';
            ptp4lElement.textContent = 'ptp4l: Остановлен';
        }
    }
}

// Загрузка PTP устройств
function loadPtpDevices() {
    // Показываем индикатор загрузки
    const sourceSelect = document.getElementById('sourcePtp');
    const targetSelect = document.getElementById('targetPtp');
    
    if (sourceSelect) {
        sourceSelect.innerHTML = '<option value="">Загрузка PTP устройств...</option>';
    }
    if (targetSelect) {
        targetSelect.innerHTML = '<option value="">Загрузка PTP устройств...</option>';
    }
    
    fetch('/api/ptp/devices')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updatePtpDeviceSelects(data.data);
                showAlert('Успех', `Загружено ${data.data.length} PTP устройств`);
            } else {
                console.error('Ошибка загрузки PTP устройств:', data.error);
                showAlert('Ошибка', 'Не удалось загрузить PTP устройства');
            }
        })
        .catch(error => {
            console.error('Ошибка запроса PTP устройств:', error);
            showAlert('Ошибка', 'Ошибка сети при загрузке PTP устройств');
        });
}

function updatePtpDeviceSelects(devices) {
    const sourceSelect = document.getElementById('sourcePtp');
    const targetSelect = document.getElementById('targetPtp');
    
    if (sourceSelect) {
        sourceSelect.innerHTML = '<option value="">Выберите источник PTP</option>';
        devices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.path;
            
            // Создаем текст с иконкой статуса
            const statusIcon = device.available ? '✅' : '❌';
            const statusText = device.available ? 'доступно' : 'недоступно';
            const pinInfo = device.pins ? ` (${device.pins})` : '';
            
            option.textContent = `${device.name} ${statusIcon} ${statusText}${pinInfo}`;
            option.disabled = !device.available;
            
            // Добавляем title для дополнительной информации
            option.title = device.pins ? `Пины: ${device.pins}` : 'Нет информации о пинах';
            
            sourceSelect.appendChild(option);
        });
    }
    
    if (targetSelect) {
        targetSelect.innerHTML = '<option value="">Выберите цель PTP</option>';
        devices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.path;
            
            // Создаем текст с иконкой статуса
            const statusIcon = device.available ? '✅' : '❌';
            const statusText = device.available ? 'доступно' : 'недоступно';
            const pinInfo = device.pins ? ` (${device.pins})` : '';
            
            option.textContent = `${device.name} ${statusIcon} ${statusText}${pinInfo}`;
            option.disabled = !device.available;
            
            // Добавляем title для дополнительной информации
            option.title = device.pins ? `Пины: ${device.pins}` : 'Нет информации о пинах';
            
            targetSelect.appendChild(option);
        });
    }
    
    // Обновляем отображение в секции PTP мониторинга
    updatePtpDevicesList(devices);
    
    // Показываем информацию о доступных устройствах
    const availableDevices = devices.filter(d => d.available);
    if (availableDevices.length > 0) {
        console.log(`Доступно PTP устройств: ${availableDevices.length}`);
        availableDevices.forEach(device => {
            console.log(`  - ${device.path}: ${device.pins || 'без информации о пинах'}`);
        });
    } else {
        console.log('PTP устройства не найдены или недоступны');
    }
}

function updatePtpDevicesList(devices) {
    const container = document.getElementById('ptpDevicesList');
    if (!container) return;
    
    if (devices.length === 0) {
        container.innerHTML = '<p class="text-muted">PTP устройства не найдены</p>';
        return;
    }
    
    let html = '<div class="row">';
    devices.forEach(device => {
        const statusClass = device.available ? 'success' : 'danger';
        const statusIcon = device.available ? '✅' : '❌';
        const statusText = device.available ? 'Доступно' : 'Недоступно';
        
        html += `
            <div class="col-md-6 mb-2">
                <div class="card border-${statusClass}">
                    <div class="card-body p-2">
                        <h6 class="card-title mb-1">
                            <i class="fas fa-microchip"></i> ${device.name}
                        </h6>
                        <p class="card-text mb-1">
                            <small class="text-${statusClass}">
                                ${statusIcon} ${statusText}
                            </small>
                        </p>
                        ${device.pins ? `<p class="card-text mb-0"><small class="text-muted">Пины: ${device.pins}</small></p>` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

// PHC Синхронизация функции
function startPhcSync() {
    const sourcePtp = document.getElementById('sourcePtp').value;
    const targetPtp = document.getElementById('targetPtp').value;
    
    if (!sourcePtp || !targetPtp) {
        showAlert('Ошибка', 'Выберите источник и цель PTP');
        return;
    }
    
    if (sourcePtp === targetPtp) {
        showAlert('Ошибка', 'Источник и цель не могут быть одинаковыми');
        return;
    }
    
    fetch('/api/sync/phc/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            source_ptp: sourcePtp,
            target_ptp: targetPtp
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успех', data.message);
        } else {
            showAlert('Ошибка', data.error);
        }
    })
    .catch(error => {
        showAlert('Ошибка', 'Ошибка сети: ' + error.message);
    });
}

function stopPhcSync() {
    fetch('/api/sync/phc/stop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успех', data.message);
        } else {
            showAlert('Ошибка', data.error);
        }
    })
    .catch(error => {
        showAlert('Ошибка', 'Ошибка сети: ' + error.message);
    });
}

function startTs2phcSync() {
    const sourcePtp = document.getElementById('sourcePtp').value;
    const targetPtp = document.getElementById('targetPtp').value;
    
    if (!sourcePtp || !targetPtp) {
        showAlert('Ошибка', 'Выберите источник и цель PTP');
        return;
    }
    
    fetch('/api/sync/ts2phc/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            source_ptp: sourcePtp,
            target_ptp: targetPtp
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успех', data.message);
        } else {
            showAlert('Ошибка', data.error);
        }
    })
    .catch(error => {
        showAlert('Ошибка', 'Ошибка сети: ' + error.message);
    });
}

function stopTs2phcSync() {
    fetch('/api/sync/ts2phc/stop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успех', data.message);
        } else {
            showAlert('Ошибка', data.error);
        }
    })
    .catch(error => {
        showAlert('Ошибка', 'Ошибка сети: ' + error.message);
    });
}

function startTimeNICPhcSync(timenicName) {
    fetch(`/api/timenics/${timenicName}/phc-sync`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успех', data.message);
            refreshTimeNICs();
        } else {
            showAlert('Ошибка', data.error);
        }
    })
    .catch(error => {
        showAlert('Ошибка', 'Ошибка сети: ' + error.message);
    });
}