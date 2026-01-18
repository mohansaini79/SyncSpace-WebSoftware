// Kanban Board Manager
class KanbanManager {
    constructor(workspaceId) {
        this.workspaceId = workspaceId;
        this.socket = socketManager.getSocket();
        this.boards = [];
        this.tasks = [];
        this.draggedTask = null;
        
        this.init();
    }

    init() {
        console.log('Initializing Kanban Manager for workspace:', this.workspaceId);
        
        // Load kanban data
        this.loadKanbanBoard();
        
        // Setup socket listeners
        this.setupSocketListeners();
        
        // Setup UI listeners
        this.setupUIListeners();
    }

    setupSocketListeners() {
        // Kanban board changed
        this.socket.on('kanban_changed', (data) => {
            if (data.workspace_id === this.workspaceId) {
                console.log('Kanban board updated by another user');
                this.loadKanbanBoard();
            }
        });
    }

    setupUIListeners() {
        const createTaskBtn = document.getElementById('createTaskBtn');
        if (createTaskBtn) {
            createTaskBtn.addEventListener('click', () => {
                this.openCreateTaskModal();
            });
        }

        const createTaskForm = document.getElementById('createTaskForm');
        if (createTaskForm) {
            createTaskForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createTask();
            });
        }
    }

    async loadKanbanBoard() {
        try {
            const response = await fetch(`/api/kanban/${this.workspaceId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.boards = data.boards || [];
                this.tasks = data.tasks || [];
                this.renderKanbanBoard();
            }
        } catch (error) {
            console.error('Error loading kanban board:', error);
        }
    }

    renderKanbanBoard() {
        const container = document.getElementById('kanbanBoard');
        if (!container) return;

        container.innerHTML = this.boards.map(board => {
            const boardTasks = this.tasks.filter(task => task.status === board.id);
            
            return `
                <div class="kanban-column bg-gray-50 rounded-lg p-4 min-w-80" data-status="${board.id}">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="font-bold text-gray-900">${board.title}</h3>
                        <span class="bg-gray-200 text-gray-700 px-2 py-1 rounded-full text-xs">${boardTasks.length}</span>
                    </div>
                    
                    <div class="kanban-tasks space-y-3 min-h-96" 
                         ondrop="kanbanManager.handleDrop(event, '${board.id}')"
                         ondragover="kanbanManager.handleDragOver(event)"
                         ondragleave="kanbanManager.handleDragLeave(event)">
                        ${boardTasks.map(task => this.renderTask(task)).join('')}
                    </div>
                    
                    ${board.id === 'todo' ? `
                        <button onclick="kanbanManager.openCreateTaskModal('${board.id}')" 
                                class="w-full mt-3 py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-blue-400 hover:text-blue-600 transition">
                            + Add Task
                        </button>
                    ` : ''}
                </div>
            `;
        }).join('');
    }

    renderTask(task) {
        const priorityColors = {
            high: 'border-l-4 border-red-500',
            medium: 'border-l-4 border-yellow-500',
            low: 'border-l-4 border-green-500'
        };

        return `
            <div class="kanban-task bg-white rounded-lg p-4 shadow hover:shadow-md transition cursor-move ${priorityColors[task.priority] || priorityColors.medium}"
                 draggable="true"
                 ondragstart="kanbanManager.handleDragStart(event, '${task._id}')"
                 ondragend="kanbanManager.handleDragEnd(event)">
                <h4 class="font-semibold text-gray-900 mb-2">${escapeHtml(task.title)}</h4>
                <p class="text-sm text-gray-600 mb-3">${escapeHtml(task.description || '')}</p>
                
                <div class="flex items-center justify-between text-xs">
                    <span class="px-2 py-1 rounded ${
                        task.priority === 'high' ? 'bg-red-100 text-red-800' :
                        task.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                    }">
                        ${task.priority || 'medium'}
                    </span>
                    
                    ${task.due_date ? `
                        <span class="text-gray-500">
                            Due ${formatRelativeTime(task.due_date)}
                        </span>
                    ` : ''}
                </div>
                
                <div class="mt-3 flex items-center justify-between">
                    <div class="flex -space-x-2">
                        ${(task.assigned_to || []).slice(0, 3).map(userId => `
                            <div class="w-6 h-6 rounded-full bg-blue-500 text-white text-xs flex items-center justify-center border-2 border-white">
                                ${getInitials(userId)}
                            </div>
                        `).join('')}
                    </div>
                    
                    <button onclick="kanbanManager.deleteTask('${task._id}')" 
                            class="text-red-500 hover:text-red-700">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }

    handleDragStart(event, taskId) {
        this.draggedTask = taskId;
        event.currentTarget.style.opacity = '0.5';
    }

    handleDragEnd(event) {
        event.currentTarget.style.opacity = '1';
        this.draggedTask = null;
    }

    handleDragOver(event) {
        event.preventDefault();
        event.currentTarget.classList.add('kanban-drag-over');
    }

    handleDragLeave(event) {
        event.currentTarget.classList.remove('kanban-drag-over');
    }

    async handleDrop(event, newStatus) {
        event.preventDefault();
        event.currentTarget.classList.remove('kanban-drag-over');

        if (!this.draggedTask) return;

        try {
            const response = await fetch(`/api/kanban/task/${this.draggedTask}/move`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: newStatus })
            });

            if (response.ok) {
                // Update local state
                const task = this.tasks.find(t => t._id === this.draggedTask);
                if (task) {
                    task.status = newStatus;
                }
                
                this.renderKanbanBoard();
                
                // Notify other users
                this.socket.emit('kanban_update', {
                    workspace_id: this.workspaceId
                });
                
                showToast('Task moved successfully', 'success');
            }
        } catch (error) {
            console.error('Error moving task:', error);
            showToast('Failed to move task', 'error');
        }
    }

    openCreateTaskModal(status = 'todo') {
        const modal = document.getElementById('createTaskModal');
        if (modal) {
            modal.classList.remove('hidden');
            document.getElementById('taskStatus').value = status;
        }
    }

    closeCreateTaskModal() {
        const modal = document.getElementById('createTaskModal');
        if (modal) {
            modal.classList.add('hidden');
            document.getElementById('createTaskForm').reset();
        }
    }

    async createTask() {
        const title = document.getElementById('taskTitle').value;
        const description = document.getElementById('taskDescription').value;
        const priority = document.getElementById('taskPriority').value;
        const status = document.getElementById('taskStatus').value;
        const dueDate = document.getElementById('taskDueDate').value;

        try {
            const response = await fetch('/api/kanban/task', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title,
                    description,
                    priority,
                    status,
                    due_date: dueDate,
                    workspace_id: this.workspaceId
                })
            });

            if (response.ok) {
                const task = await response.json();
                this.tasks.push(task);
                this.renderKanbanBoard();
                this.closeCreateTaskModal();
                
                // Notify other users
                this.socket.emit('kanban_update', {
                    workspace_id: this.workspaceId
                });
                
                showToast('Task created successfully', 'success');
            } else {
                showToast('Failed to create task', 'error');
            }
        } catch (error) {
            console.error('Error creating task:', error);
            showToast('Failed to create task', 'error');
        }
    }

    async deleteTask(taskId) {
        if (!confirm('Delete this task?')) return;

        try {
            const response = await fetch(`/api/kanban/task/${taskId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.ok) {
                this.tasks = this.tasks.filter(t => t._id !== taskId);
                this.renderKanbanBoard();
                
                // Notify other users
                this.socket.emit('kanban_update', {
                    workspace_id: this.workspaceId
                });
                
                showToast('Task deleted successfully', 'success');
            }
        } catch (error) {
            console.error('Error deleting task:', error);
            showToast('Failed to delete task', 'error');
        }
    }

    destroy() {
        this.socket.off('kanban_changed');
    }
}
