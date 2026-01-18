// Main JavaScript Utilities for SyncSpace

// Authentication
function getToken() {
    return localStorage.getItem('token');
}

function getUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

function isLoggedIn() {
    return !!getToken() && !!getUser();
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}

// API Calls
async function apiCall(endpoint, method = 'GET', body = null) {
    const token = getToken();
    const headers = {'Content-Type': 'application/json'};
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const options = {method, headers};
    
    if (body && method !== 'GET') {
        options.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(endpoint, options);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Toast Notifications
function showToast(message, type = 'success', duration = 3000) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    
    if (!toast || !toastMessage) return;
    
    toastMessage.textContent = message;
    
    toast.classList.remove('bg-green-500', 'bg-red-500', 'bg-blue-500', 'bg-yellow-500');
    
    switch(type) {
        case 'success':
            toast.classList.add('bg-green-500');
            break;
        case 'error':
            toast.classList.add('bg-red-500');
            break;
        case 'info':
            toast.classList.add('bg-blue-500');
            break;
        case 'warning':
            toast.classList.add('bg-yellow-500');
            break;
        default:
            toast.classList.add('bg-green-500');
    }
    
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, duration);
}

// Date Formatting
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Validation
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePassword(password) {
    return password.length >= 6;
}

// Export
window.SyncSpace = {
    getToken,
    getUser,
    isLoggedIn,
    logout,
    apiCall,
    showToast,
    formatDate,
    formatDateTime,
    validateEmail,
    validatePassword
};

// Auto-redirect on protected pages
document.addEventListener('DOMContentLoaded', () => {
    console.log('✓ SyncSpace Main.js loaded');
    
    const protectedPaths = ['/dashboard', '/workspace'];
    const currentPath = window.location.pathname;
    
    if (protectedPaths.some(path => currentPath.startsWith(path)) && !isLoggedIn()) {
        window.location.href = '/login';
    }
});
