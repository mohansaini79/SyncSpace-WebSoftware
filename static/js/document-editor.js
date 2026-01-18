// Document Editor Manager
class DocumentEditor {
    constructor(documentId) {
        this.documentId = documentId;
        this.socket = socketManager.getSocket();
        this.currentUser = getCurrentUser();
        this.editor = null;
        this.saveTimeout = null;
        this.isTyping = false;
        
        this.init();
    }

    init() {
        console.log('Initializing Document Editor for document:', this.documentId);
        
        // Load document
        this.loadDocument();
        
        // Setup socket listeners
        this.setupSocketListeners();
        
        // Setup editor listeners
        this.setupEditorListeners();
        
        // Join document room
        this.socket.emit('join_document', {
            document_id: this.documentId,
            user_id: this.currentUser.id,
            username: this.currentUser.name
        });
    }

    setupSocketListeners() {
        // Document updated by another user
        this.socket.on('document_updated', (data) => {
            if (data.user_id !== this.currentUser.id) {
                console.log('Document updated by:', data.username);
                this.updateEditorContent(data.content, false);
            }
        });

        // User joined document
        this.socket.on('user_joined_document', (data) => {
            console.log('User joined:', data.username);
            this.showNotification(`${data.username} joined the document`, 'info');
            this.updateActiveUsers();
        });

        // User left document
        this.socket.on('user_left_document', (data) => {
            console.log('User left:', data.username);
            this.updateActiveUsers();
        });

        // User typing indicator
        this.socket.on('user_typing_document', (data) => {
            this.showTypingIndicator(data.username, data.typing);
        });

        // Cursor position update
        this.socket.on('cursor_position_update', (data) => {
            this.showRemoteCursor(data);
        });
    }

    setupEditorListeners() {
        this.editor = document.getElementById('documentEditor');
        
        if (!this.editor) {
            console.error('Document editor element not found');
            return;
        }

        // Content change
        this.editor.addEventListener('input', () => {
            this.handleContentChange();
        });

        // Typing indicator
        this.editor.addEventListener('keydown', () => {
            this.handleTypingStart();
        });

        // Stop typing after 2 seconds
        this.editor.addEventListener('keyup', () => {
            clearTimeout(this.typingTimeout);
            this.typingTimeout = setTimeout(() => {
                this.handleTypingStop();
            }, 2000);
        });

        // Cursor position tracking
        this.editor.addEventListener('click', () => {
            this.handleCursorMove();
        });

        this.editor.addEventListener('keyup', () => {
            this.handleCursorMove();
        });
    }

    async loadDocument() {
        try {
            const response = await fetch(`/api/document/${this.documentId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.ok) {
                const document = await response.json();
                
                // Update title
                const titleElement = document.getElementById('documentTitle');
                if (titleElement) {
                    titleElement.textContent = document.title || 'Untitled Document';
                }

                // Update content
                if (this.editor) {
                    this.editor.innerHTML = document.content || '<p>Start typing...</p>';
                }

                // Update active users
                this.updateActiveUsers(document.active_users);
            }
        } catch (error) {
            console.error('Error loading document:', error);
            showToast('Failed to load document', 'error');
        }
    }

    handleContentChange() {
        const content = this.editor.innerHTML;

        // Emit change to other users
        this.socket.emit('document_content_change', {
            document_id: this.documentId,
            content: content,
            username: this.currentUser.name,
            user_id: this.currentUser.id
        });

        // Auto-save after 2 seconds of inactivity
        clearTimeout(this.saveTimeout);
        this.saveTimeout = setTimeout(() => {
            this.saveDocument(content);
        }, 2000);

        // Update save status
        this.updateSaveStatus('Saving...');
    }

    async saveDocument(content) {
        try {
            const response = await fetch(`/api/document/${this.documentId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content })
            });

            if (response.ok) {
                this.updateSaveStatus('All changes saved');
            } else {
                this.updateSaveStatus('Failed to save');
            }
        } catch (error) {
            console.error('Error saving document:', error);
            this.updateSaveStatus('Failed to save');
        }
    }

    updateEditorContent(content, emitChange = true) {
        if (this.editor) {
            // Save cursor position
            const selection = window.getSelection();
            const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;

            // Update content
            this.editor.innerHTML = content;

            // Restore cursor position (if possible)
            if (range && emitChange) {
                try {
                    selection.removeAllRanges();
                    selection.addRange(range);
                } catch (e) {
                    // Cursor restoration failed, ignore
                }
            }
        }
    }

    handleTypingStart() {
        if (!this.isTyping) {
            this.isTyping = true;
            this.socket.emit('document_typing', {
                document_id: this.documentId,
                username: this.currentUser.name
            });
        }
    }

    handleTypingStop() {
        if (this.isTyping) {
            this.isTyping = false;
            this.socket.emit('document_stop_typing', {
                document_id: this.documentId,
                username: this.currentUser.name
            });
        }
    }

    handleCursorMove() {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const position = {
                offset: range.startOffset,
                node: range.startContainer.nodeName
            };

            // Throttle cursor position updates
            clearTimeout(this.cursorTimeout);
            this.cursorTimeout = setTimeout(() => {
                this.socket.emit('document_cursor_position', {
                    document_id: this.documentId,
                    user_id: this.currentUser.id,
                    username: this.currentUser.name,
                    position: position
                });
            }, 200);
        }
    }

    showTypingIndicator(username, typing) {
        let indicator = document.getElementById('typingIndicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'typingIndicator';
            indicator.className = 'fixed bottom-4 left-4 bg-white shadow-lg rounded-lg px-4 py-2 text-sm text-gray-600';
            document.body.appendChild(indicator);
        }

        if (typing) {
            indicator.innerHTML = `
                <div class="flex items-center gap-2">
                    <span>${escapeHtml(username)} is typing</span>
                    <div class="flex gap-1">
                        <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                        <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                        <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                    </div>
                </div>
            `;
            indicator.style.display = 'block';
        } else {
            indicator.style.display = 'none';
        }
    }

    showRemoteCursor(data) {
        let cursor = document.getElementById(`cursor-${data.user_id}`);
        
        if (!cursor) {
            cursor = document.createElement('div');
            cursor.id = `cursor-${data.user_id}`;
            cursor.className = 'remote-cursor';
            cursor.style.backgroundColor = generateRandomColor();
            cursor.innerHTML = `<div class="cursor-flag" style="background-color: ${cursor.style.backgroundColor}">${escapeHtml(data.username)}</div>`;
            document.body.appendChild(cursor);
        }

        // Update cursor position (simplified - would need more complex logic in production)
        cursor.style.left = `${Math.random() * 80 + 10}%`;
        cursor.style.top = `${Math.random() * 80 + 10}%`;
    }

    updateActiveUsers(users = []) {
        const container = document.getElementById('activeUsers');
        if (!container) return;

        if (users.length === 0) {
            container.innerHTML = '<span class="text-sm text-gray-500">Only you</span>';
            return;
        }

        container.innerHTML = `
            <div class="flex items-center gap-2">
                <span class="text-sm text-gray-600">${users.length} active</span>
                <div class="flex -space-x-2">
                    ${users.slice(0, 5).map(user => `
                        <div class="w-8 h-8 rounded-full bg-blue-500 text-white text-xs flex items-center justify-center border-2 border-white" title="${escapeHtml(user.username)}">
                            ${getInitials(user.username)}
                        </div>
                    `).join('')}
                    ${users.length > 5 ? `<div class="w-8 h-8 rounded-full bg-gray-300 text-gray-700 text-xs flex items-center justify-center border-2 border-white">+${users.length - 5}</div>` : ''}
                </div>
            </div>
        `;
    }

    updateSaveStatus(status) {
        const statusElement = document.getElementById('saveStatus');
        if (statusElement) {
            statusElement.textContent = status;
            
            if (status.includes('saved')) {
                statusElement.className = 'text-xs text-green-600';
            } else if (status.includes('Failed')) {
                statusElement.className = 'text-xs text-red-600';
            } else {
                statusElement.className = 'text-xs text-gray-500';
            }
        }
    }

    showNotification(message, type = 'info') {
        showToast(message, type, 2000);
    }

    // Formatting functions
    formatText(command, value = null) {
        document.execCommand(command, false, value);
        this.editor.focus();
        this.handleContentChange();
    }

    destroy() {
        // Leave document room
        this.socket.emit('leave_document', {
            document_id: this.documentId,
            user_id: this.currentUser.id,
            username: this.currentUser.name
        });

        // Remove socket listeners
        this.socket.off('document_updated');
        this.socket.off('user_joined_document');
        this.socket.off('user_left_document');
        this.socket.off('user_typing_document');
        this.socket.off('cursor_position_update');

        // Clear timeouts
        clearTimeout(this.saveTimeout);
        clearTimeout(this.typingTimeout);
        clearTimeout(this.cursorTimeout);
    }
}

// Auto-initialize when on document page
document.addEventListener('DOMContentLoaded', () => {
    const pathParts = window.location.pathname.split('/');
    if (pathParts[1] === 'document' && pathParts[2]) {
        const documentId = pathParts[2];
        window.documentEditor = new DocumentEditor(documentId);
    }
});
