/**
 * Система уведомлений для SHIWA NIC-PPS
 */

class NotificationManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Создаем контейнер для уведомлений
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        // Иконки для разных типов
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        // Цвета для разных типов
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        };

        notification.style.cssText = `
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-left: 4px solid ${colors[type]};
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            margin-bottom: 12px;
            padding: 20px;
            display: flex;
            align-items: center;
            animation: slideIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            position: relative;
            border: 1px solid rgba(255, 255, 255, 0.2);
        `;

        notification.innerHTML = `
            <i class="${icons[type]}" style="color: ${colors[type]}; margin-right: 10px; font-size: 18px;"></i>
            <span style="flex: 1; color: #333;">${message}</span>
            <button class="btn-close" style="background: none; border: none; font-size: 18px; cursor: pointer; color: #999; margin-left: 10px;">&times;</button>
        `;

        // Добавляем CSS анимацию
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
                .notification {
                    transition: all 0.3s ease;
                }
                .notification.slide-out {
                    animation: slideOut 0.3s ease-in forwards;
                }
            `;
            document.head.appendChild(style);
        }

        // Обработчик закрытия
        const closeBtn = notification.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => {
            this.remove(notification);
        });

        this.container.appendChild(notification);

        // Автоматическое удаление
        if (duration > 0) {
            setTimeout(() => {
                this.remove(notification);
            }, duration);
        }

        return notification;
    }

    remove(notification) {
        if (notification && notification.parentNode) {
            notification.classList.add('slide-out');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }

    success(message, duration = 5000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 8000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 6000) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 5000) {
        return this.show(message, 'info', duration);
    }

    clear() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Глобальный экземпляр
window.notificationManager = new NotificationManager();

// Удобные функции
window.showSuccess = (message, duration) => window.notificationManager.success(message, duration);
window.showError = (message, duration) => window.notificationManager.error(message, duration);
window.showWarning = (message, duration) => window.notificationManager.warning(message, duration);
window.showInfo = (message, duration) => window.notificationManager.info(message, duration);
