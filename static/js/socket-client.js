// Global Socket.IO connection manager
class SocketManager {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.currentUser = JSON.parse(localStorage.getItem('user') || '{}');
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        if (this.socket && this.connected) {
            console.log('Already connected');
            return this.socket;
        }

        // Connect to Socket.IO server with eventlet settings
        this.socket = io('http://localhost:5000', {
            transports: ['polling', 'websocket'],  // Try polling first
            upgrade: true,
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: this.maxReconnectAttempts,
            timeout: 10000
        });

        // Connection successful
        this.socket.on('connect', () => {
            console.log('✅ Socket.IO Connected:', this.socket.id);
            this.connected = true;
            this.reconnectAttempts = 0;
            this.showConnectionStatus('Connected', 'success');

            // Subscribe to user notifications
            if (this.currentUser.id) {
                this.socket.emit('subscribe_notifications', {
                    user_id: this.currentUser.id
                });

                // Mark user as online
                this.socket.emit('user_online', {
                    user_id: this.currentUser.id,
                    username: this.currentUser.name
                });
            }
        });

        // Disconnection
        this.socket.on('disconnect', (reason) => {
            console.log('❌ Socket.IO Disconnected:', reason);
            this.connected = false;
            this.showConnectionStatus('Disconnected', 'error');
        });

        // Reconnection attempt
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`🔄 Reconnection attempt ${attemptNumber}...`);
            this.reconnectAttempts = attemptNumber;
        });

        // Reconnection successful
        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`✅ Reconnected after ${attemptNumber} attempts`);
            this.showConnectionStatus('Reconnected', 'success');
        });

        // Reconnection failed
        this.socket.on('reconnect_failed', () => {
            console.log('❌ Reconnection failed');
            this.showConnectionStatus('Connection failed', 'error');
        });

        // Server confirmation
        this.socket.on('connected', (data) => {
            console.log('Server says:', data.data);
        });

        // Connection error
        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
        });

        return this.socket;
    }

    disconnect() {
        if (this.socket) {
            // Mark user as offline
            if (this.currentUser.id) {
                this.socket.emit('user_offline', {
                    user_id: this.currentUser.id
                });
            }

            this.socket.disconnect();
            this.connected = false;
            console.log('Socket.IO disconnected by user');
        }
    }

    getSocket() {
        if (!this.socket || !this.connected) {
            return this.connect();
        }
        return this.socket;
    }

    isConnected() {
        return this.connected && this.socket && this.socket.connected;
    }

    showConnectionStatus(message, type) {
        let statusDiv = document.getElementById('connectionStatus');
        
        if (!statusDiv) {
            statusDiv = document.createElement('div');
            statusDiv.id = 'connectionStatus';
            statusDiv.className = 'fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-lg text-white text-sm z-50 transition-all';
            document.body.appendChild(statusDiv);
        }

        const colors = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        };

        statusDiv.className = `fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-lg text-white text-sm z-50 transition-all ${colors[type] || colors.info}`;
        statusDiv.textContent = message;
        statusDiv.style.display = 'block';

        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 3000);
    }

    emit(event, data) {
        if (this.isConnected()) {
            this.socket.emit(event, data);
        } else {
            console.error('Cannot emit event: Socket not connected');
            this.connect();
        }
    }

    on(event, callback) {
        if (this.socket) {
            this.socket.on(event, callback);
        } else {
            console.error('Cannot listen to event: Socket not initialized');
        }
    }

    off(event, callback) {
        if (this.socket) {
            this.socket.off(event, callback);
        }
    }
}

// Create global instance
const socketManager = new SocketManager();

// Auto-connect when user is logged in
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (token) {
        socketManager.connect();
    }
});

// Disconnect on page unload
window.addEventListener('beforeunload', () => {
    socketManager.disconnect();
});
