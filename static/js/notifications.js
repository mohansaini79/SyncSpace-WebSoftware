// Notification Manager
class NotificationManager {
    constructor() {
        this.socket = socketManager.getSocket();
        this.currentUser = getCurrentUser();
        this.notifications = [];
        this.unreadCount = 0;
        
        this.init();
    }

    init() {
        console.log('Initializing Notification Manager');
        
        // Load initial notifications
        this.loadNotifications();
        
        // Setup socket listeners
        this.setupSocketListeners();
        
        // Setup UI listeners
        this.setupUIListeners();
        
        // Request notification permission
        this.requestNotificationPermission();
    }

    setupSocketListeners() {
        // Live notification received
        this.socket.on('live_notification', (data) => {
            console.log('Live notification received:', data);
            this.addNotification(data);
            this.showBrowserNotification(data);
            this.playNotificationSound();
        });
    }

    setupUIListeners() {
        const notificationBtn = document.getElementById('notificationBtn');
        const notificationDropdown = document.getElementById('notificationDropdown');
        const clearBtn = document.getElementById('clearNotificationsBtn');

        if (notificationBtn) {
            notificationBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleNotificationDropdown();
            });
        }

        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearAllNotifications();
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (notificationDropdown && !notificationDropdown.contains(e.target) && e.target !== notificationBtn) {
                notificationDropdown.classList.add('hidden');
            }
        });
    }

    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.notifications = data.notifications || [];
                this.unreadCount = data.unread_count || 0;
                this.updateUI();
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    addNotification(notificationData) {
        // Add to beginning of array
        this.notifications.unshift({
            message: notificationData.message,
            type: notificationData.type || 'info',
            read: false,
            created_at: new Date().toISOString()
        });

        this.unreadCount++;
        this.updateUI();
    }

    updateUI() {
        // Update badge
        const badge = document.getElementById('notificationBadge');
        const count = document.getElementById('notificationCount');

        if (badge && count) {
            if (this.unreadCount > 0) {
                badge.classList.remove('hidden');
                count.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
            } else {
                badge.classList.add('hidden');
            }
        }

        // Update list
        this.renderNotificationList();
    }

    renderNotificationList() {
        const container = document.getElementById('notificationsList');
        if (!container) return;

        if (this.notifications.length === 0) {
            container.innerHTML = `
                <div class="p-8 text-center text-gray-500">
                    <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
                    </svg>
                    <p>No notifications yet</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.notifications.map(notif => `
            <div class="p-4 border-b hover:bg-gray-50 transition ${notif.read ? 'bg-white' : 'bg-blue-50'}">
                <div class="flex items-start gap-3">
                    <div class="flex-shrink-0">
                        ${this.getNotificationIcon(notif.type)}
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm text-gray-900">${escapeHtml(notif.message)}</p>
                        <p class="text-xs text-gray-500 mt-1">${formatRelativeTime(notif.created_at)}</p>
                    </div>
                    ${!notif.read ? '<div class="w-2 h-2 bg-blue-600 rounded-full"></div>' : ''}
                </div>
            </div>
        `).join('');
    }

    getNotificationIcon(type) {
        const icons = {
            mention: '<svg class="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6z"></path></svg>',
            task_assignment: '<svg class="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20"><path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"></path><path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm9.707 5.707a1 1 0 00-1.414-1.414L9 12.586l-1.293-1.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>',
            info: '<svg class="w-5 h-5 text-gray-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>'
        };
        return icons[type] || icons.info;
    }

    toggleNotificationDropdown() {
        const dropdown = document.getElementById('notificationDropdown');
        if (!dropdown) return;

        const isHidden = dropdown.classList.contains('hidden');
        
        if (isHidden) {
            dropdown.classList.remove('hidden');
            // Mark as read after opening
            if (this.unreadCount > 0) {
                setTimeout(() => this.markAllAsRead(), 1000);
            }
        } else {
            dropdown.classList.add('hidden');
        }
    }

    async markAllAsRead() {
        try {
            await fetch('/api/notifications/read', {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            this.notifications = this.notifications.map(n => ({ ...n, read: true }));
            this.unreadCount = 0;
            this.updateUI();
        } catch (error) {
            console.error('Error marking notifications as read:', error);
        }
    }

    async clearAllNotifications() {
        if (!confirm('Clear all notifications?')) return;

        try {
            await fetch('/api/notifications/', {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            this.notifications = [];
            this.unreadCount = 0;
            this.updateUI();
            showToast('Notifications cleared', 'success');
        } catch (error) {
            console.error('Error clearing notifications:', error);
            showToast('Failed to clear notifications', 'error');
        }
    }

    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }

    showBrowserNotification(data) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('SyncSpace', {
                body: data.message,
                icon: '/static/images/logo.png',
                badge: '/static/images/badge.png'
            });
        }
    }

    playNotificationSound() {
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYHGGS57OihUBELTKXh8LJnHgU2jdXzzn0vBSh+zPDejz0JFF607uypWRQLRp/f8r9vIgUrhM/y2Ik2BxhluevooVARC0yl4fCyZx4FNo3V8859LwUofsz');
            audio.volume = 0.3;
            audio.play().catch(() => {});
        } catch (error) {
            // Silently fail if audio not supported
        }
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (isAuthenticated()) {
        window.notificationManager = new NotificationManager();
    }
});
