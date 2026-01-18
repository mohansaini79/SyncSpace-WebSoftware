// Dashboard Manager
class DashboardManager {
    constructor() {
        this.currentUser = getCurrentUser();
        this.workspaces = [];
        this.projects = [];
        this.tasks = [];
        
        this.init();
    }

    init() {
        console.log('Initializing Dashboard Manager');
        
        // Load all data
        this.loadDashboardData();
        
        // Setup refresh button
        const refreshBtn = document.getElementById('refreshDashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadDashboardData();
            });
        }

        // Setup create workspace button
        const createWorkspaceBtn = document.getElementById('createWorkspaceBtn');
        if (createWorkspaceBtn) {
            createWorkspaceBtn.addEventListener('click', () => {
                document.getElementById('createWorkspaceModal').classList.remove('hidden');
            });
        }
    }

    async loadDashboardData() {
        this.showLoader(true);
        
        try {
            await Promise.all([
                this.loadWorkspaces(),
                this.loadProjects(),
                this.loadMyTasks()
            ]);
            
            this.updateStatistics();
        } catch (error) {
            console.error('Error loading dashboard:', error);
            showToast('Failed to load dashboard data', 'error');
        } finally {
            this.showLoader(false);
        }
    }

    async loadWorkspaces() {
        try {
            const response = await fetch('/api/workspace/list', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.workspaces = data.workspaces || [];
                this.renderWorkspaces();
            }
        } catch (error) {
            console.error('Error loading workspaces:', error);
        }
    }

    async loadProjects() {
        try {
            const response = await fetch('/api/project/list', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.projects = data.projects || [];
                this.renderProjects();
            }
        } catch (error) {
            console.error('Error loading projects:', error);
        }
    }

    async loadMyTasks() {
        try {
            const response = await fetch('/api/kanban/my-tasks', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.tasks = data.tasks || [];
                this.renderTasks();
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
        }
    }

    updateStatistics() {
        // Update stat cards
        document.getElementById('totalWorkspaces').textContent = this.workspaces.length;
        document.getElementById('totalProjects').textContent = this.projects.length;
        document.getElementById('totalTasks').textContent = this.tasks.length;
        
        const completedTasks = this.tasks.filter(t => t.status === 'done').length;
        document.getElementById('completedTasks').textContent = completedTasks;
    }

    renderWorkspaces() {
        const container = document.getElementById('workspacesContainer');
        if (!container) return;

        if (this.workspaces.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <svg class="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                    </svg>
                    <p class="text-gray-500 mb-4">No workspaces yet</p>
                    <button onclick="document.getElementById('createWorkspaceModal').classList.remove('hidden')" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                        Create Your First Workspace
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = this.workspaces.map(workspace => `
            <div class="workspace-card bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition cursor-pointer" onclick="window.location.href='/workspace/${workspace._id}'">
                <div class="flex items-center justify-between mb-4">
                    <div class="bg-blue-100 rounded-lg p-3">
                        <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                        </svg>
                    </div>
                    <span class="text-xs text-gray-500">${workspace.members?.length || 0} members</span>
                </div>
                <h3 class="text-lg font-bold text-gray-900 mb-2">${escapeHtml(workspace.name)}</h3>
                <p class="text-sm text-gray-600 mb-4">${escapeHtml(workspace.description || 'No description')}</p>
                <div class="flex items-center justify-between text-xs text-gray-500">
                    <span>Created ${formatRelativeTime(workspace.created_at)}</span>
                    <span class="text-blue-600 font-medium">Open →</span>
                </div>
            </div>
        `).join('');
    }

    renderProjects() {
        const container = document.getElementById('projectsContainer');
        if (!container) return;

        if (this.projects.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-8 text-gray-500">
                    <p>No projects yet</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.projects.slice(0, 6).map(project => `
            <div class="bg-white rounded-lg shadow p-4 hover:shadow-md transition">
                <div class="flex items-center gap-3 mb-3">
                    <div class="bg-purple-100 rounded p-2">
                        <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                        </svg>
                    </div>
                    <div class="flex-1">
                        <h4 class="font-semibold text-gray-900">${escapeHtml(project.name)}</h4>
                        <p class="text-xs text-gray-500">${project.tasks_count || 0} tasks</p>
                    </div>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-blue-600 h-2 rounded-full" style="width: ${project.progress || 0}%"></div>
                </div>
                <p class="text-xs text-gray-500 mt-2">${project.progress || 0}% complete</p>
            </div>
        `).join('');
    }

    renderTasks() {
        const container = document.getElementById('tasksContainer');
        if (!container) return;

        if (this.tasks.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                    </svg>
                    <p>No tasks assigned</p>
                </div>
            `;
            return;
        }

        const priorityColors = {
            high: 'bg-red-100 text-red-800',
            medium: 'bg-yellow-100 text-yellow-800',
            low: 'bg-green-100 text-green-800'
        };

        container.innerHTML = this.tasks.slice(0, 10).map(task => `
            <div class="bg-white rounded-lg shadow p-3 hover:shadow-md transition">
                <div class="flex items-start justify-between mb-2">
                    <h5 class="font-medium text-gray-900 text-sm">${escapeHtml(task.title)}</h5>
                    <span class="px-2 py-1 rounded text-xs ${priorityColors[task.priority] || priorityColors.medium}">
                        ${task.priority || 'medium'}
                    </span>
                </div>
                <p class="text-xs text-gray-600 mb-2">${escapeHtml(task.description || '')}</p>
                <div class="flex items-center justify-between">
                    <span class="text-xs text-gray-500">${formatRelativeTime(task.created_at)}</span>
                    ${task.status === 'done' ? 
                        '<span class="text-xs text-green-600 font-medium">✓ Done</span>' : 
                        '<span class="text-xs text-blue-600 font-medium">In Progress</span>'
                    }
                </div>
            </div>
        `).join('');
    }

    showLoader(show) {
        const loader = document.getElementById('dashboardLoader');
        if (loader) {
            if (show) {
                loader.classList.remove('hidden');
            } else {
                loader.classList.add('hidden');
            }
        }
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (isAuthenticated() && window.location.pathname === '/dashboard') {
        window.dashboardManager = new DashboardManager();
    }
});
