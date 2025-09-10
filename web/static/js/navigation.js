/**
 * Улучшенная система навигации для SHIWA NIC-PPS
 */

class NavigationManager {
    constructor() {
        this.currentTab = 'overview';
        this.history = ['overview'];
        this.init();
    }

    init() {
        this.setupTabListeners();
        this.setupBreadcrumbs();
        this.setupKeyboardNavigation();
    }

    setupTabListeners() {
        // Слушаем переключение вкладок
        document.addEventListener('shown.bs.tab', (event) => {
            const tabId = event.target.getAttribute('data-bs-target').substring(1);
            this.switchTab(tabId);
        });

        // Добавляем анимации при переключении
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                this.animateTabSwitch(e.target);
            });
        });
    }

    switchTab(tabId) {
        this.currentTab = tabId;
        this.history.push(tabId);
        
        // Обновляем хлебные крошки
        this.updateBreadcrumbs();
        
        // Добавляем анимацию появления контента
        const tabContent = document.getElementById(tabId);
        if (tabContent) {
            tabContent.classList.add('fade-in');
        }

        // Специальные действия для разных вкладок
        this.handleTabSpecificActions(tabId);
    }

    animateTabSwitch(clickedTab) {
        // Анимация для активной вкладки
        document.querySelectorAll('.nav-link').forEach(tab => {
            tab.classList.remove('pulse');
        });
        clickedTab.classList.add('pulse');
        
        // Убираем анимацию через 1 секунду
        setTimeout(() => {
            clickedTab.classList.remove('pulse');
        }, 1000);
    }

    handleTabSpecificActions(tabId) {
        switch(tabId) {
            case 'metrics':
                // Автоматически обновляем метрики при переходе
                if (typeof refreshMetrics === 'function') {
                    setTimeout(refreshMetrics, 100);
                }
                break;
            case 'monitoring':
                // Загружаем Chart.js если нужно
                if (typeof loadChartJS === 'function') {
                    loadChartJS();
                }
                break;
            case 'timenic':
                // Обновляем TimeNIC данные
                if (typeof refreshTimeNICs === 'function') {
                    setTimeout(refreshTimeNICs, 100);
                }
                break;
        }
    }

    setupBreadcrumbs() {
        // Создаем хлебные крошки
        const breadcrumbContainer = document.createElement('div');
        breadcrumbContainer.id = 'breadcrumb-container';
        breadcrumbContainer.className = 'breadcrumb-container';
        breadcrumbContainer.style.cssText = `
            padding: 12px 24px;
            background: rgba(248, 250, 252, 0.8);
            border-bottom: 1px solid var(--border-color);
            font-size: 0.875rem;
        `;

        // Вставляем после навигации
        const navTabs = document.querySelector('.nav-tabs');
        if (navTabs) {
            navTabs.parentNode.insertBefore(breadcrumbContainer, navTabs.nextSibling);
        }

        this.updateBreadcrumbs();
    }

    updateBreadcrumbs() {
        const container = document.getElementById('breadcrumb-container');
        if (!container) return;

        const tabNames = {
            'overview': 'Обзор',
            'timenic': 'TimeNIC',
            'config': 'Настройки',
            'metrics': 'Метрики',
            'monitoring': 'Мониторинг'
        };

        const currentName = tabNames[this.currentTab] || this.currentTab;
        
        container.innerHTML = `
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb mb-0">
                    <li class="breadcrumb-item">
                        <i class="fas fa-home me-1"></i>
                        <a href="#" onclick="navigationManager.goToTab('overview')" class="text-decoration-none">Главная</a>
                    </li>
                    <li class="breadcrumb-item active" aria-current="page">
                        <i class="fas fa-${this.getTabIcon(this.currentTab)} me-1"></i>
                        ${currentName}
                    </li>
                </ol>
            </nav>
        `;
    }

    getTabIcon(tabId) {
        const icons = {
            'overview': 'home',
            'timenic': 'clock',
            'config': 'cog',
            'metrics': 'chart-bar',
            'monitoring': 'chart-line'
        };
        return icons[tabId] || 'circle';
    }

    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Alt + цифра для быстрого переключения вкладок
            if (e.altKey && e.key >= '1' && e.key <= '5') {
                e.preventDefault();
                const tabIndex = parseInt(e.key) - 1;
                const tabs = document.querySelectorAll('.nav-link');
                if (tabs[tabIndex]) {
                    tabs[tabIndex].click();
                }
            }
        });
    }

    goToTab(tabId) {
        const tab = document.querySelector(`[data-bs-target="#${tabId}"]`);
        if (tab) {
            tab.click();
        }
    }

    goBack() {
        if (this.history.length > 1) {
            this.history.pop(); // Убираем текущую вкладку
            const previousTab = this.history[this.history.length - 1];
            this.goToTab(previousTab);
        }
    }

    // Показываем подсказки для быстрого доступа
    showKeyboardShortcuts() {
        if (window.showInfo) {
            window.showInfo(`
                <strong>Горячие клавиши:</strong><br>
                Alt + 1 - Обзор<br>
                Alt + 2 - TimeNIC<br>
                Alt + 3 - Настройки<br>
                Alt + 4 - Метрики<br>
                Alt + 5 - Мониторинг
            `, 8000);
        }
    }
}

// Глобальный экземпляр
window.navigationManager = new NavigationManager();

// Показываем подсказки при первом запуске
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        if (window.navigationManager) {
            window.navigationManager.showKeyboardShortcuts();
        }
    }, 3000);
});
