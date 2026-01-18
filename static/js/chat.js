// Chat Manager for real-time messaging
class ChatManager {
    constructor(workspaceId) {
        this.workspaceId = workspaceId;
        this.socket = socketManager.getSocket();
        this.currentUser = getCurrentUser();
        this.typingTimeout = null;
        
        this.init();
    }

    init() {
        console.log('Initializing Chat Manager for workspace:', this.workspaceId);
        
        // Load initial messages
        this.loadMessages();
        
        // Setup event listeners
        this.setupSocketListeners();
        this.setupUIListeners();
    }

    setupSocketListeners() {
        // New message received
        this.socket.on('new_message', (data) => {
            this.displayMessage(data);
            this.scrollToBottom();
        });

        // User typing indicator
        this.socket.on('user_typing', (data) => {
            this.showTypingIndicator(data.username, data.typing);
        });
    }

    setupUIListeners() {
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendMessageBtn');

        if (messageInput) {
            // Send message on Enter
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Typing indicator
            messageInput.addEventListener('input', () => {
                this.handleTyping();
            });
        }

        if (sendButton) {
            sendButton.addEventListener('click', () => {
                this.sendMessage();
            });
        }
    }

    async loadMessages() {
        try {
            const response = await fetch(`/api/chat/${this.workspaceId}/messages`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.ok) {
                const messages = await response.json();
                this.displayAllMessages(messages);
                this.scrollToBottom();
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }

    sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();

        if (!message) return;

        // Emit to server via Socket.IO
        this.socket.emit('chat_message', {
            workspace_id: this.workspaceId,
            user_id: this.currentUser.id,
            username: this.currentUser.name,
            message: message
        });

        // Clear input
        messageInput.value = '';
        
        // Stop typing indicator
        this.socket.emit('typing_stop', {
            workspace_id: this.workspaceId,
            username: this.currentUser.name
        });
    }

    displayAllMessages(messages) {
        const container = document.getElementById('chatMessages');
        if (!container) return;

        container.innerHTML = '';

        messages.forEach(msg => {
            this.displayMessage(msg, false);
        });
    }

    displayMessage(data, animate = true) {
        const container = document.getElementById('chatMessages');
        if (!container) return;

        const isOwnMessage = data.user_id === this.currentUser.id;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex ${isOwnMessage ? 'justify-end' : 'justify-start'} mb-4 ${animate ? 'animate-fade-in' : ''}`;
        
        const time = formatRelativeTime(data.timestamp);
        
        messageDiv.innerHTML = `
            <div class="max-w-xs lg:max-w-md">
                ${!isOwnMessage ? `<p class="text-xs text-gray-600 mb-1">${escapeHtml(data.username)}</p>` : ''}
                <div class="${isOwnMessage ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-900'} rounded-lg px-4 py-2">
                    <p class="text-sm break-words">${this.formatMessage(data.message)}</p>
                </div>
                <p class="text-xs text-gray-500 mt-1 ${isOwnMessage ? 'text-right' : ''}">${time}</p>
            </div>
        `;

        container.appendChild(messageDiv);
    }

    formatMessage(message) {
        // Escape HTML
        let formatted = escapeHtml(message);
        
        // Highlight mentions
        formatted = formatted.replace(/@(\w+)/g, '<span class="font-bold bg-yellow-200 px-1 rounded">@$1</span>');
        
        // Convert URLs to links
        formatted = formatted.replace(
            /(https?:\/\/[^\s]+)/g,
            '<a href="$1" target="_blank" class="underline">$1</a>'
        );
        
        return formatted;
    }

    handleTyping() {
        // Emit typing start
        this.socket.emit('typing_start', {
            workspace_id: this.workspaceId,
            username: this.currentUser.name
        });

        // Clear existing timeout
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }

        // Set timeout to emit typing stop
        this.typingTimeout = setTimeout(() => {
            this.socket.emit('typing_stop', {
                workspace_id: this.workspaceId,
                username: this.currentUser.name
            });
        }, 2000);
    }

    showTypingIndicator(username, typing) {
        let indicator = document.getElementById('typingIndicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'typingIndicator';
            indicator.className = 'text-sm text-gray-500 italic px-4 py-2';
            
            const container = document.getElementById('chatMessages');
            if (container && container.parentNode) {
                container.parentNode.insertBefore(indicator, container.nextSibling);
            }
        }

        if (typing) {
            indicator.innerHTML = `
                <div class="flex items-center gap-2">
                    <span>${escapeHtml(username)} is typing</span>
                    <div class="flex gap-1">
                        <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0s"></div>
                        <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                        <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
                    </div>
                </div>
            `;
            indicator.style.display = 'block';
        } else {
            indicator.style.display = 'none';
        }
    }

    scrollToBottom() {
        const container = document.getElementById('chatMessages');
        if (container) {
            setTimeout(() => {
                container.scrollTop = container.scrollHeight;
            }, 100);
        }
    }

    destroy() {
        // Remove socket listeners
        this.socket.off('new_message');
        this.socket.off('user_typing');
    }
}
