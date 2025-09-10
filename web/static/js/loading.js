/**
 * Система индикаторов загрузки для SHIWA NIC-PPS
 */

class LoadingManager {
    constructor() {
        this.activeLoaders = new Set();
        this.init();
    }

    init() {
        // Создаем глобальный overlay для загрузки
        this.overlay = document.createElement('div');
        this.overlay.id = 'global-loading-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        `;
        
        this.overlay.innerHTML = `
            <div class="loading-spinner" style="
                background: white;
                padding: 30px;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            ">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Загрузка...</span>
                </div>
                <div class="mt-3" id="loading-message">Загрузка...</div>
            </div>
        `;
        
        document.body.appendChild(this.overlay);
    }

    showGlobal(message = 'Загрузка...') {
        const messageEl = this.overlay.querySelector('#loading-message');
        if (messageEl) {
            messageEl.textContent = message;
        }
        this.overlay.style.display = 'flex';
    }

    hideGlobal() {
        this.overlay.style.display = 'none';
    }

    showElement(element, message = 'Загрузка...') {
        if (!element) return;

        const loaderId = `loader-${Date.now()}-${Math.random()}`;
        this.activeLoaders.add(loaderId);

        // Создаем индикатор загрузки
        const loader = document.createElement('div');
        loader.id = loaderId;
        loader.className = 'element-loader';
        loader.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            border-radius: inherit;
            border: 1px solid rgba(255, 255, 255, 0.2);
        `;

        loader.innerHTML = `
            <div class="text-center">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Загрузка...</span>
                </div>
                <div class="mt-2 small text-muted">${message}</div>
            </div>
        `;

        // Делаем родительский элемент относительно позиционированным
        const originalPosition = element.style.position;
        if (originalPosition === '' || originalPosition === 'static') {
            element.style.position = 'relative';
        }

        element.appendChild(loader);
        return loaderId;
    }

    hideElement(loaderId) {
        if (!this.activeLoaders.has(loaderId)) return;

        const loader = document.getElementById(loaderId);
        if (loader && loader.parentNode) {
            loader.parentNode.removeChild(loader);
        }
        this.activeLoaders.delete(loaderId);
    }

    showButton(button, message = 'Загрузка...') {
        if (!button) return;

        const originalText = button.innerHTML;
        const originalDisabled = button.disabled;

        button.disabled = true;
        button.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            ${message}
        `;

        return {
            restore: () => {
                button.disabled = originalDisabled;
                button.innerHTML = originalText;
            }
        };
    }

    showTable(table, message = 'Загрузка данных...') {
        if (!table) return;

        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        const originalContent = tbody.innerHTML;
        tbody.innerHTML = `
            <tr>
                <td colspan="100%" class="text-center py-4">
                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                    ${message}
                </td>
            </tr>
        `;

        return {
            restore: () => {
                tbody.innerHTML = originalContent;
            }
        };
    }

    showCard(card, message = 'Загрузка...') {
        if (!card) return;

        const cardBody = card.querySelector('.card-body');
        if (!cardBody) return;

        const originalContent = cardBody.innerHTML;
        cardBody.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Загрузка...</span>
                </div>
                <div class="mt-2 text-muted">${message}</div>
            </div>
        `;

        return {
            restore: () => {
                cardBody.innerHTML = originalContent;
            }
        };
    }

    // Утилиты для часто используемых операций
    async withLoading(promise, options = {}) {
        const {
            global = false,
            element = null,
            message = 'Загрузка...',
            successMessage = null,
            errorMessage = 'Произошла ошибка'
        } = options;

        let loaderId = null;
        let buttonRestore = null;

        try {
            if (global) {
                this.showGlobal(message);
            } else if (element) {
                loaderId = this.showElement(element, message);
            }

            const result = await promise;

            if (successMessage && window.showSuccess) {
                window.showSuccess(successMessage);
            }

            return result;
        } catch (error) {
            if (errorMessage && window.showError) {
                window.showError(errorMessage);
            }
            throw error;
        } finally {
            if (global) {
                this.hideGlobal();
            } else if (loaderId) {
                this.hideElement(loaderId);
            } else if (buttonRestore) {
                buttonRestore.restore();
            }
        }
    }
}

// Глобальный экземпляр
window.loadingManager = new LoadingManager();

// Удобные функции
window.showLoading = (message) => window.loadingManager.showGlobal(message);
window.hideLoading = () => window.loadingManager.hideGlobal();
window.withLoading = (promise, options) => window.loadingManager.withLoading(promise, options);
