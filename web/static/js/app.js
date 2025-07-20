// Глобальные переменные
let socket = null;
let trafficChart = null;
let temperatureChart = null;
let monitoringData = {};
let currentMonitoringInterface = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    refreshNICs();
    initializeCharts();
    
    // Обработчики событий
    document.getElementById('nicSelect').addEventListener('change', onNicSelectChange);
    document.getElementById('monitorNicSelect').addEventListener('change', onMonitorNicSelectChange);
    document.getElementById('configFile').addEventListener('change', onConfigFileChange);
});

// Инициализация WebSocket соединения
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        updateConnectionStatus(true);
    });
    
    socket.on('disconnect', function() {
        updateConnectionStatus(false);
    });
    
    socket.on('monitoring_data', function(data) {
        updateMonitoringData(data);
    });
}

// Обновление статуса соединения
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (connected) {
        statusElement.innerHTML = '<i class="fas fa-circle text-success"></i> Подключено';
    } else {
        statusElement.innerHTML = '<i class="fas fa-circle text-danger"></i> Отключено';
    }
}

// Обновление списка NIC карт
function refreshNICs() {
    fetch('/api/nics')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateNICTable(data.data);
                updateNICSelects(data.data);
            } else {
                showAlert('Ошибка', 'Не удалось загрузить список NIC карт: ' + data.error);
            }
        })
        .catch(error => {
            showAlert('Ошибка', 'Ошибка сети: ' + error.message);
        });
}

// Обновление таблицы NIC карт
function updateNICTable(nics) {
    const tbody = document.getElementById('nicTableBody');
    tbody.innerHTML = '';
    
    if (nics.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">NIC карты не обнаружены</td></tr>';
        return;
    }
    
    nics.forEach(nic => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${nic.name}</strong></td>
            <td><code>${nic.mac_address}</code></td>
            <td>${nic.ip_address || 'N/A'}</td>
            <td><span class="badge ${nic.status === 'up' ? 'bg-success' : 'bg-danger'}">${nic.status}</span></td>
            <td>${nic.speed}</td>
            <td><span class="badge bg-info">${nic.pps_mode}</span></td>
            <td><i class="fas fa-${nic.tcxo_enabled ? 'check text-success' : 'times text-danger'}"></i></td>
            <td>${nic.temperature ? nic.temperature.toFixed(1) + '°C' : 'N/A'}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary btn-sm" onclick="configureNIC('${nic.name}')">
                        <i class="fas fa-cog"></i>
                    </button>
                    <button class="btn btn-outline-info btn-sm" onclick="showNICInfo('${nic.name}')">
                        <i class="fas fa-info"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Обновление селектов NIC карт
function updateNICSelects(nics) {
    const nicSelect = document.getElementById('nicSelect');
    const monitorNicSelect = document.getElementById('monitorNicSelect');
    
    // Очищаем существующие опции
    nicSelect.innerHTML = '<option value="">Выберите карту...</option>';
    monitorNicSelect.innerHTML = '<option value="">Выберите карту...</option>';
    
    nics.forEach(nic => {
        const option1 = document.createElement('option');
        option1.value = nic.name;
        option1.textContent = `${nic.name} (${nic.mac_address})`;
        nicSelect.appendChild(option1);
        
        const option2 = document.createElement('option');
        option2.value = nic.name;
        option2.textContent = `${nic.name} (${nic.mac_address})`;
        monitorNicSelect.appendChild(option2);
    });
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
    // График трафика
    const trafficCtx = document.getElementById('trafficChart').getContext('2d');
    trafficChart = new Chart(trafficCtx, {
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
                    beginAtZero: true
                }
            }
        }
    });
    
    // График температуры
    const tempCtx = document.getElementById('temperatureChart').getContext('2d');
    temperatureChart = new Chart(tempCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Температура (°C)',
                data: [],
                borderColor: 'rgb(255, 159, 64)',
                backgroundColor: 'rgba(255, 159, 64, 0.2)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Запуск мониторинга
function startMonitoring() {
    const nicName = document.getElementById('monitorNicSelect').value;
    if (!nicName) {
        showAlert('Ошибка', 'Выберите NIC карту для мониторинга');
        return;
    }
    
    fetch('/api/monitoring/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ interfaces: [nicName] })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('startMonitoring').disabled = true;
            document.getElementById('stopMonitoring').disabled = false;
            showAlert('Успех', 'Мониторинг запущен');
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
            document.getElementById('startMonitoring').disabled = false;
            document.getElementById('stopMonitoring').disabled = true;
            showAlert('Успех', 'Мониторинг остановлен');
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
    monitoringData = data;
    updateCharts();
    updateStats();
}

// Обновление графиков
function updateCharts() {
    if (!currentMonitoringInterface || !monitoringData[currentMonitoringInterface]) {
        return;
    }
    
    const data = monitoringData[currentMonitoringInterface];
    const timestamp = new Date().toLocaleTimeString();
    
    // Обновляем график трафика
    if (data.stats) {
        const rxSpeed = data.stats.rx_bytes || 0;
        const txSpeed = data.stats.tx_bytes || 0;
        
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
    
    // Обновляем график температуры
    if (data.temperature) {
        temperatureChart.data.labels.push(timestamp);
        temperatureChart.data.datasets[0].data.push(data.temperature);
        
        // Ограничиваем количество точек
        if (temperatureChart.data.labels.length > 20) {
            temperatureChart.data.labels.shift();
            temperatureChart.data.datasets[0].data.shift();
        }
        
        temperatureChart.update();
    }
}

// Обновление статистики
function updateStats() {
    if (!currentMonitoringInterface || !monitoringData[currentMonitoringInterface]) {
        return;
    }
    
    const data = monitoringData[currentMonitoringInterface];
    const statsDiv = document.getElementById('statsDisplay');
    
    let statsHtml = '';
    if (data.stats) {
        statsHtml = `
            <div class="row">
                <div class="col-6">
                    <strong>Принято пакетов:</strong><br>
                    <strong>Отправлено пакетов:</strong><br>
                    <strong>Ошибки приема:</strong><br>
                    <strong>Ошибки отправки:</strong><br>
                </div>
                <div class="col-6">
                    ${data.stats.rx_packets || 0}<br>
                    ${data.stats.tx_packets || 0}<br>
                    ${data.stats.rx_errors || 0}<br>
                    ${data.stats.tx_errors || 0}<br>
                </div>
            </div>
        `;
    }
    
    if (data.temperature) {
        statsHtml += `<hr><strong>Температура:</strong> ${data.temperature.toFixed(1)}°C`;
    }
    
    if (data.status) {
        statsHtml += `<hr><strong>Статус:</strong> <span class="badge ${data.status === 'up' ? 'bg-success' : 'bg-danger'}">${data.status}</span>`;
    }
    
    statsDiv.innerHTML = statsHtml || '<p class="text-muted">Нет данных</p>';
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