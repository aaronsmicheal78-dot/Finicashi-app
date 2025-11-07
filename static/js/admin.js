// class AdminDashboard {
//     constructor() {
//         this.currentSection = 'dashboard';
//         this.adminData = null;
//         this.dashboardMetrics = null;
//         this.init();
//     }

//     async init() {
//         await this.loadAdminData();
//         this.initializeEventListeners();
//         this.renderDashboard();
//         this.startLiveUpdates();
//     }

//     // Unified API fetcher with error handling
//     async apiFetch(url, options = {}) {
//         const defaultOptions = {
//             method: 'GET',
//             headers: {
//                 'Content-Type': 'application/json',
//                 'X-Requested-With': 'XMLHttpRequest'
//             },
//             credentials: 'same-origin', // ensures session cookies are sent
//             ...options
//         };

//         try {
//             const response = await fetch(url, defaultOptions);

//             // Handle non-JSON or network errors
//             if (!response.ok) {
//                 let message = `Request failed: ${response.status} ${response.statusText}`;
//                 try {
//                     const errorData = await response.json();
//                     message = errorData.message || errorData.error || message;
//                 } catch (e) {
//                     // Response not JSON—keep default message
//                 }
//                 throw new Error(message);
//             }

//             // Handle JSON parsing
//             const contentType = response.headers.get('content-type');
//             if (contentType && contentType.includes('application/json')) {
//                 return await response.json();
//             } else {
//                 throw new Error('Invalid response: expected JSON');
//             }
//         } catch (error) {
//             console.error(`API Error (${url}):`, error);
//             this.showNotification(`Error: ${error.message}`, 'error');
//             return null;
//         }
//     }

//     showNotification(message, type = 'info') {
//         // Create or reuse a toast container
//         let toastContainer = document.getElementById('admin-toast-container');
//         if (!toastContainer) {
//             toastContainer = document.createElement('div');
//             toastContainer.id = 'admin-toast-container';
//             toastContainer.style.cssText = `
//                 position: fixed;
//                 top: 20px;
//                 right: 20px;
//                 z-index: 10000;
//                 max-width: 400px;
//             `;
//             document.body.appendChild(toastContainer);
//         }

//         const toast = document.createElement('div');
//         toast.className = `admin-toast admin-toast-${type}`;
//         toast.style.cssText = `
//             background: ${type === 'error' ? '#fee' : type === 'success' ? '#efe' : '#eef'};
//             color: ${type === 'error' ? '#c33' : type === 'success' ? '#282' : '#228'};
//             border-left: 4px solid ${type === 'error' ? '#c33' : type === 'success' ? '#282' : '#258'};
//             padding: 12px 16px;
//             margin-bottom: 10px;
//             border-radius: 4px;
//             box-shadow: 0 2px 8px rgba(0,0,0,0.15);
//             animation: fadeIn 0.3s;
//         `;
//         toast.innerHTML = `<strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${message}`;

//         toastContainer.appendChild(toast);

//         // Auto-remove after 5s
//         setTimeout(() => {
//             toast.style.animation = 'fadeOut 0.5s';
//             setTimeout(() => toast.remove(), 500);
//         }, 5000);
//     }

//     // --- Data Loading ---
//     async loadAdminData() {
//         const adminData = localStorage.getItem('fincashpro_admin_data');
//         if (adminData) {
//             try {
//                 this.adminData = JSON.parse(adminData);
//                 this.updateUserInfo();
//             } catch (e) {
//                 console.warn('Invalid admin data in localStorage');
//             }
//         }
//         await this.refreshAllData();
//     }

//     initializeEventListeners() {
//         document.querySelectorAll('.admin-nav-item').forEach(item => {
//             item.addEventListener('click', (e) => {
//                 e.preventDefault();
//                 this.switchSection(item.dataset.section);
//             });
//         });

//         document.getElementById('admin-refresh-data')?.addEventListener('click', () => {
//             this.refreshAllData();
//         });

//         // Modal close buttons
//         ['payment', 'bonus', 'user', 'message', 'confirm'].forEach(type => {
//             const btn = document.getElementById(`admin-close-${type}-modal`);
//             btn?.addEventListener('click', () => this.closeModal(type));
//         });

//         document.getElementById('admin-user-menu')?.addEventListener('click', () => {
//             this.showUserMenu();
//         });
//     }

//     // --- Navigation ---
//     switchSection(section) {
//         this.currentSection = section;
//         document.querySelectorAll('.admin-nav-item').forEach(item => {
//             item.classList.toggle('active', item.dataset.section === section);
//         });

//         const titles = {
//             'dashboard': 'Dashboard Overview',
//             'payment-requests': 'Payment Requests',
//             'bonus-requests': 'Bonus Requests',
//             'user-management': 'User Management',
//             'messages': 'User Messages',
//             'reports': 'System Reports',
//             'system': 'System Settings'
//         };
//         document.getElementById('admin-current-section').textContent = titles[section] || 'Admin Panel';

//         this.renderSection(section);
//     }

//     renderSection(section) {
//         const contentArea = document.getElementById('admin-dynamic-content');
//         if (!contentArea) return;

//         let html = '';
//         switch (section) {
//             case 'dashboard': html = this.renderDashboardContent(); break;
//             case 'payment-requests': html = this.renderPaymentRequests(); break;
//             case 'bonus-requests': html = this.renderBonusRequests(); break;
//             case 'user-management': html = this.renderUserManagement(); break;
//             case 'messages': html = this.renderMessages(); break;
//             case 'reports': html = this.renderReports(); break;
//             case 'system': html = this.renderSystemSettings(); break;
//             default: html = '<p>Section not found</p>';
//         }
//         contentArea.innerHTML = html;
//     }

//     // --- Dashboard Rendering ---
//     renderDashboard() {
//         this.renderStatsGrid(); // Will be populated by updateStats()
//         this.renderSection('dashboard');
//     }

//     renderStatsGrid(data = null) {
//         const statsGrid = document.getElementById('admin-stats-grid');
//         if (!statsGrid) return;

//         if (!data) {
//             statsGrid.innerHTML = `
//                 <div class="admin-stat-card loading">loading...</div>
//                 <div class="admin-stat-card loading">Loading...</div>
//                 <div class="admin-stat-card loading">Loading...</div>
//                 <div class="admin-stat-card loading">Loading...</div>
//                 <div class="admin-stat-card loading">Loading...</div>
//                 <div class="admin-stat-card loading">Loading...</div>
//             `;
//             return;
//         }

//         const stats = [
//             { label: 'Total Users', value: data.total_users.toLocaleString(), type: 'users' },
//             { label: 'Pending Payments', value: data.pending_payments.toLocaleString(), type: 'payments' },
//             { label: 'Total Bonuses', value: `$${data.total_bonuses.toFixed(2)}`, type: 'bonuses' },
//             { label: 'Total Volume', value: `$${data.total_balances.toFixed(2)}`, type: 'volume' },
//             { label: 'New Users (24h)', value: data.new_users_24h.toLocaleString(), type: 'users' },
//             { label: 'Failed Logins (24h)', value: data.failed_logins_24h.toLocaleString(), type: 'security' }
//         ];

//         statsGrid.innerHTML = stats.map(stat => `
//             <div class="admin-stat-card ${stat.type}">
//                 <div class="admin-stat-value">${stat.value}</div>
//                 <div class="admin-stat-label">${stat.label}</div>
//             </div>
//         `).join('');
//     }

//     renderDashboardContent() {
//         return `
//             <div class="admin-content-section">
//                 <div class="admin-section-header">
//                     <h3 class="admin-section-title">Recent Activity</h3>
//                     <div class="admin-section-actions">
//                         <button class="admin-action-btn view" id="view-all-activity">View All</button>
//                     </div>
//                 </div>
//                 <div class="admin-section-body">
//                     <p class="admin-no-data">Recent activity feed will appear here soon.</p>
//                 </div>
//             </div>

//             <div class="admin-content-section">
//                 <div class="admin-section-header">
//                     <h3 class="admin-section-title">Quick Actions</h3>
//                 </div>
//                 <div class="admin-section-body">
//                     <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
//                         <button class="admin-action-btn view" id="quick-view-payments">Review Payments</button>
//                         <button class="admin-action-btn approve" id="quick-process-bonuses">Process Bonuses</button>
//                         <button class="admin-action-btn edit" id="quick-user-search">Search Users</button>
//                         <button class="admin-action-btn view" id="quick-generate-report">Generate Report</button>
//                     </div>
//                 </div>
//             </div>
//         `;
//     }

//     // --- Other Section Templates (unchanged) ---
//     renderPaymentRequests() {
//         return `
//             <div class="admin-content-section">
//                 <div class="admin-section-header">
//                     <h3 class="admin-section-title">Pending Payment Requests</h3>
//                     <div class="admin-section-actions">
//                         <button class="admin-action-btn view" id="export-payments">Export</button>
//                         <button class="admin-action-btn approve" id="bulk-approve-payments">Bulk Approve</button>
//                     </div>
//                 </div>
//                 <div class="admin-section-body">
//                     <p class="admin-no-data">Payment requests will load here.</p>
//                 </div>
//             </div>
//         `;
//     }

//     renderBonusRequests() {
//         return `
//             <div class="admin-content-section">
//                 <div class="admin-section-header">
//                     <h3 class="admin-section-title">Pending Bonus Requests</h3>
//                     <div class="admin-section-actions">
//                         <button class="admin-action-btn view" id="export-bonuses">Export</button>
//                         <button class="admin-action-btn approve" id="bulk-approve-bonuses">Bulk Approve</button>
//                     </div>
//                 </div>
//                 <div class="admin-section-body">
//                     <p class="admin-no-data">Bonus requests will load here.</p>
//                 </div>
//             </div>
//         `;
//     }

//     renderUserManagement() {
//         return `
//             <div class="admin-content-section">
//                 <div class="admin-section-header">
//                     <h3 class="admin-section-title">User Management</h3>
//                     <div class="admin-section-actions">
//                         <input type="text" id="user-search-input" placeholder="Search users..." class="admin-form-input" style="width: 300px;">
//                         <button class="admin-action-btn view" id="search-users">Search</button>
//                     </div>
//                 </div>
//                 <div class="admin-section-body">
//                     <p class="admin-no-data">User list will appear after search.</p>
//                 </div>
//             </div>
//         `;
//     }

//     renderMessages() {
//         return `
//             <div class="admin-content-section">
//                 <div class="admin-section-header">
//                     <h3 class="admin-section-title">User Messages</h3>
//                     <div class="admin-section-actions">
//                         <button class="admin-action-btn view" id="mark-all-read">Mark All Read</button>
//                     </div>
//                 </div>
//                 <div class="admin-section-body">
//                     <p class="admin-no-data">Messages will load here.</p>
//                 </div>
//             </div>
//         `;
//     }

//     renderReports() {
//         return `
//             <div class="admin-content-section">
//                 <div class="admin-section-header">
//                     <h3 class="admin-section-title">System Reports</h3>
//                     <div class="admin-section-actions">
//                         <button class="admin-action-btn view" id="generate-financial-report">Financial Report</button>
//                         <button class="admin-action-btn view" id="generate-user-report">User Report</button>
//                     </div>
//                 </div>
//                 <div class="admin-section-body">
//                     <div id="reports-container">
//                         <p>Generate reports using the buttons above.</p>
//                     </div>
//                 </div>
//             </div>
//         `;
//     }

//     renderSystemSettings() {
//         return `
//             <div class="admin-content-section">
//                 <div class="admin-section-header">
//                     <h3 class="admin-section-title">System Configuration</h3>
//                 </div>
//                 <div class="admin-section-body">
//                     <form id="system-settings-form">
//                         <div class="admin-form-group">
//                             <label class="admin-form-label">System Maintenance Mode</label>
//                             <select class="admin-form-select" id="maintenance-mode">
//                                 <option value="false">Disabled</option>
//                                 <option value="true">Enabled</option>
//                             </select>
//                         </div>
//                         <div class="admin-form-group">
//                             <label class="admin-form-label">Auto-approve Payments Under ($)</label>
//                             <input type="number" step="0.01" class="admin-form-input" id="auto-approve-limit" placeholder="0.00">
//                         </div>
//                         <div class="admin-form-group">
//                             <label class="admin-form-label">System Notification Email</label>
//                             <input type="email" class="admin-form-input" id="notification-email" placeholder="admin@fincashpro.com">
//                         </div>
//                         <button type="submit" class="admin-action-btn approve">Save Settings</button>
//                     </form>
//                 </div>
//             </div>
//         `;
//     }

//     // --- Data Refresh ---
//     async refreshAllData() {
//         await this.updateStats();
//         // Later: await this.updatePaymentRequests(); etc.
//     }

//     async updateStats() {
//         const metrics = await this.apiFetch('/admin/dashboard/data');
//         if (metrics) {
//             this.dashboardMetrics = metrics;
//             this.renderStatsGrid(metrics);
//         } else {
//             this.renderStatsGrid(null); // show loading/error
//         }
//     }

//     // --- Modals & Utils ---
//     closeModal(type) {
//         const modal = document.getElementById(`admin-${type}-modal`);
//         if (modal) modal.classList.remove('show');
//     }

//     updateUserInfo() {
//         if (this.adminData) {
//             const usernameEl = document.getElementById('admin-username');
//             const avatarEl = document.getElementById('admin-user-avatar');
//             if (usernameEl) usernameEl.textContent = this.adminData.username;
//             if (avatarEl) avatarEl.textContent = this.adminData.username.charAt(0).toUpperCase();
//         }
//     }

//     showUserMenu() {
//         // Implement dropdown logic if needed
//         console.log('User menu toggled');
//     }

//     startLiveUpdates() {
//         // Refresh stats every 30 seconds
//         setInterval(() => {
//             if (this.currentSection === 'dashboard') {
//                 this.updateStats();
//             }
//         }, 30000);
//     }
// }

// // Inject CSS for toasts if not present
// (function injectToastCSS() {
//     if (document.getElementById('admin-toast-styles')) return;
//     const style = document.createElement('style');
//     style.id = 'admin-toast-styles';
//     style.textContent = `
//         @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
//         @keyframes fadeOut { from { opacity: 1; transform: translateY(0); } to { opacity: 0; transform: translateY(-10px); } }
//         .admin-toast { font-size: 14px; }
//     `;
//     document.head.appendChild(style);
// })();

// // Initialize when DOM is ready
// document.addEventListener('DOMContentLoaded', () => {
//     window.adminDashboard = new AdminDashboard();
// });




//     async function fetchAdminData() {
//         const valueEl = document.getElementById('total-users-value');
//         const valueE2 = document.getElementById('total-users-active');
//         if (!valueEl) return; // Exit if element not found

//         // Show loading state
//         valueEl.textContent = 'Loading...';
//         valueEl.style.opacity = '0.7';

//         try {
//             const response = await fetch('/admin/data', {
//                 method: 'GET',
//                 headers: {
//                     'Accept': 'application/json'
//                 },
//                 credentials: 'same-origin' // Ensures session cookies are sent
//             });

//             if (!response.ok) {
//                 throw new Error(`HTTP ${response.status}`);
//             }

//             const data = await response.json();

//             // Update UI with real number (formatted)
//             if (typeof data.total_users === 'number',
//                 typeof data.total_active_users === 'number'
//             ) {
//                 valueEl.textContent = data.total_users.toLocaleString();
//                 valueEl.textContent = data.total_active_users.toLocaleString();
//             } 
//                 else {
//                 throw new Error('Invalid data format');}
                
            

//         } 
        
//         catch (error) {
//             console.error('Failed to load total users:', error);
//             valueEl.textContent = 'Error';
//             valueEl.style.color = '#e53e3e'; // Red for error
//         } finally {
//             valueEl.style.opacity = '1';
//         }
//     }

//     // Fetch when DOM is ready
//     document.addEventListener('DOMContentLoaded', () => {
//         fetchAdminData();
//     });
















// admin-dashboard.js
/**
 * Finicashi Admin Dashboard JavaScript
 * Professional, maintainable admin dashboard data management
 * Fetches data from Flask backend and dynamically updates the UI
 */
console.log("🚀 Admin dashboard script loaded");
// Configuration and Constants
const CONFIG = {
    API_BASE_URL: '',
    ENDPOINTS: {
        ADMIN_DATA: '/admin/data',
        USER_SEARCH: '/admin/search/users'
    },
    REFRESH_INTERVAL: 30000, // 30 seconds
    DEBOUNCE_DELAY: 500 // Search debounce delay
};

// Application State Management
const AppState = {
    adminData: null,
    lastUpdate: null,
    isLoading: false,
    searchQuery: '',
    currentView: 'dashboard'
};

// DOM Elements Cache
const DOM = {
    elements: {},
    
    // Initialize DOM element references
    init: function() {
        try {
            this.elements = {
                // Stats elements
                totalPayments: document.getElementById('total-payments'),
                totalUsers: document.getElementById('total-users'),
                activeUsers: document.getElementById('active-users'),
                dailyUsers: document.getElementById('daily-new-users'),
                totalBonus: document.getElementById('total-bonus'),
                pendingBonus: document.getElementById('pending-bonus'),
                pendingPayments: document.getElementById('pending-payments'),
                dailyInvestments: document.getElementById('daily-investments'),
                dailyPayouts: document.getElementById('daily-payouts'),

                
                // Change indicators
                paymentsChange: document.getElementById('payments-change'),
                usersChange: document.getElementById('users-change'),
                
                // Payment status elements
                successfulPayments: document.getElementById('successful-payments'),
                successfulAmount: document.getElementById('successful-amount'),
                pendingPaymentsCount: document.getElementById('pending-payments-count'),
                pendingAmount: document.getElementById('pending-amount'),
                failedPayments: document.getElementById('failed-payments'),
                failedAmount: document.getElementById('failed-amount'),
                declinedPayments: document.getElementById('declined-payments'),
                declinedAmount: document.getElementById('declined-amount'),
                cancelledPayments: document.getElementById('cancelled-payments'),
                cancelledAmount: document.getElementById('cancelled-amount'),
                
                // Alert badges
                pendingPaymentsBadge: document.getElementById('pending-payments-badge'),
                pendingBonusesBadge: document.getElementById('pending-bonuses-badge'),
                
                // Tables
                paymentsTableBody: document.getElementById('payments-table-body'),
                
                // Charts
                usersChart: document.getElementById('users-chart'),
                investmentsChart: document.getElementById('investments-chart'),
                
                // Search and controls
                adminSearchInput: document.getElementById('admin-search-input'),
                adminName: document.getElementById('admin-name'),
                
                // Navigation
                navDashboard: document.getElementById('nav-dashboard'),
                navUsers: document.getElementById('nav-users'),
                navPayments: document.getElementById('nav-payments'),
                navBonuses: document.getElementById('nav-bonuses'),
                navReports: document.getElementById('nav-reports'),
                navSettings: document.getElementById('nav-settings'),
                navLogout: document.getElementById('nav-logout'),
                
                // Quick actions
                actionAddUser: document.getElementById('action-add-user'),
                actionProcessBonus: document.getElementById('action-process-bonus'),
                actionManualPayment: document.getElementById('action-manual-payment'),
                actionGenerateReport: document.getElementById('action-generate-report'),
                actionSystemBackup: document.getElementById('action-system-backup'),
                actionBulkActions: document.getElementById('action-bulk-actions'),
                
                // View all links
                viewAllPayments: document.getElementById('view-all-payments')
            };
            
            // Validate critical elements exist
            this.validateRequiredElements();
            
        } catch (error) {
            console.error('DOM initialization failed:', error);
            this.showFatalError('Failed to initialize dashboard. Please refresh the page.');
        }
    },
    
    // Validate that critical elements exist
    validateRequiredElements: function() {
        const criticalElements = [
            'totalPayments', 'totalUsers', 'activeUsers', 'totalBonus',
            'pendingBonus', 'pendingPayments', 'paymentsTableBody'
        ];
        
        criticalElements.forEach(elementId => {
            if (!this.elements[elementId]) {
                throw new Error(`Critical element missing: ${elementId}`);
            }
        });
    },
    
    // Safe element text content update
    safeUpdateText: function(element, text) {
        if (element && typeof text !== 'undefined') {
            element.textContent = text;
        }
    },
    
    // Safe element HTML update
    safeUpdateHTML: function(element, html) {
        if (element && typeof html !== 'undefined') {
            element.innerHTML = html;
        }
    },
    
    // Show fatal error message
    showFatalError: function(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'fatal-error';
        errorDiv.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: #f44336;
            color: white;
            padding: 1rem;
            text-align: center;
            z-index: 10000;
            font-weight: bold;
        `;
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);
    }
};

// API Service Layer
const APIService = {
    /**
     * Generic API request handler
     */
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${CONFIG.API_BASE_URL}${endpoint}`;
        
        const config = {
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                ...options.headers
            },
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Validate response structure
            if (!this.validateResponse(data)) {
                throw new Error('Invalid response format from server');
            }
            
            return data;
            
        } catch (error) {
            console.error(`API request failed for ${endpoint}:`, error);
            throw error;
        }
    },
    
    /**
     * Validate API response structure
     */
    validateResponse(data) {
        return data && typeof data === 'object';
    },
    
    /**
     * Fetch admin dashboard data
     */
    async fetchAdminData() {
        try {
            const data = await this.request(CONFIG.ENDPOINTS.ADMIN_DATA);
            return data;
        } catch (error) {
            console.error('Failed to fetch admin data:', error);
            throw new Error('Unable to load dashboard data. Please try again.');
        }
    },
    




    
    /**
     * Search users
     */
    async searchUsers(query) {
        if (!query || query.length < 2) return { users: [] };
        
        try {
            const data = await this.request(CONFIG.ENDPOINTS.USER_SEARCH, {
                method: 'POST',
                body: JSON.stringify({ query })
            });
            return data;
        } catch (error) {
            console.error('User search failed:', error);
            throw new Error('Search failed. Please try again.');
        }
    }
};

// ... after DOM and APIService definitions ...

// ✅ Add your updateDashboard function here
async function updateDashboard() {
    try {
        const stats = await APIService.fetchAdminData();
        
        console.log("✅ Raw API response:", stats);
        console.log("🔢 total_users =", stats.total_users);
        console.log("🧱 DOM element (total-users):", DOM.elements.totalUsers);

        const formattedTotal = Formatters.formatNumber(stats.total_users);
        console.log("🖨️ Formatted:", formattedTotal);

        DOM.safeUpdateText(DOM.elements.totalUsers, formattedTotal);
        DOM.safeUpdateText(DOM.elements.activeUsers, Formatters.formatNumber(stats.active_users));
        
    } catch (err) {
        console.error("Update failed:", err);
    }
}

// ... rest of your code ...



// Data Formatters and Utilities
const Formatters = {
    /**
     * Format currency values
     */
    formatCurrency(amount, currency = 'UGX') {
        if (typeof amount !== 'number') return '0';
        
        return new Intl.NumberFormat('en-UG', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    },
    
    /**
     * Format large numbers with abbreviations
     */
    formatNumber(num) {
        if (typeof num !== 'number') return '0';
        
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    },
    
    /**
     * Format percentage changes
     */
    formatChange(change) {
        if (typeof change !== 'number') return '';
        
        const sign = change >= 0 ? '+' : '';
        return `${sign}${change.toFixed(1)}%`;
    },
    
    /**
     * Format date for display
     */
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        
        try {
            return new Date(dateString).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return 'Invalid Date';
        }
    },
    
    /**
     * Generate status badge HTML
     */
    getStatusBadge(status, amount = null) {
        const statusConfig = {
            completed: { class: 'status-success', text: 'Completed' },
            pending: { class: 'status-warning', text: 'Pending' },
            failed: { class: 'status-danger', text: 'Failed' },
            declined: { class: 'status-info', text: 'Declined' },
            cancelled: { class: 'status-warning', text: 'Cancelled' }
        };
        
        const config = statusConfig[status] || { class: 'status-info', text: status };
        const amountText = amount ? ` (${this.formatCurrency(amount)})` : '';
        
        return `<span class="status-badge ${config.class}">${config.text}${amountText}</span>`;
    }
};

// UI Update Manager
const UIManager = {
    /**
     * Update all dashboard statistics
     */
    // updateStats(data) {
    //     if (!data || !data.stats) return;
        
    //     const stats = data.stats;
        
    //     // Update main statistics
    //     DOM.safeUpdateText(DOM.elements.totalPayments, Formatters.formatCurrency(stats.total_payments));
    //     DOM.safeUpdateText(DOM.elements.totalUsers, Formatters.formatNumber(stats.total_users));
    //     DOM.safeUpdateText(DOM.elements.activeUsers, Formatters.formatNumber(stats.active_users));
    //     DOM.safeUpdateText(DOM.elements.totalBonus, Formatters.formatCurrency(stats.total_bonus));
    //     DOM.safeUpdateText(DOM.elements.pendingBonus, Formatters.formatCurrency(stats.pending_bonus));
    //     DOM.safeUpdateText(DOM.elements.pendingPayments, Formatters.formatNumber(stats.pending_payments));
    //     DOM.safeUpdateText(DOM.elements.dailyInvestments, Formatters.formatCurrency(stats.daily_investments));
    //     DOM.safeUpdateText(DOM.elements.dailyPayouts, Formatters.formatCurrency(stats.daily_payouts));
        
       updateStats(data) {
    if (!data) return;
    
    const stats = data.stats || data; // fallback to top-level
    DOM.safeUpdateText(DOM.elements.totalPayments, Formatters.formatNumber(stats.total_payments));
    DOM.safeUpdateText(DOM.elements.totalUsers, Formatters.formatNumber(stats.total_users));
    DOM.safeUpdateText(DOM.elements.activeUsers, Formatters.formatNumber(stats.active_users));
    DOM.safeUpdateText(DOM.elements.totalBonus, Formatters.formatNumber(stats.total_bonus));
    DOM.safeUpdateText(DOM.elements.pendingBonus, Formatters.formatCurrency(stats.pending_bonus));
    DOM.safeUpdateText(DOM.elements.pendingPayments, Formatters.formatNumber(stats.pending_payments));
    DOM.safeUpdateText(DOM.elements.dailyInvestments, Formatters.formatCurrency(stats.daily_investments || 0));
    DOM.safeUpdateText(DOM.elements.dailyPayouts, Formatters.formatCurrency(stats.daily_payouts));
    DOM.safeUpdateText(DOM.elements.dailyUsers, Formatters.formatNumber(stats.daily_new_users));
        // Update change indicators
        this.updateChangeIndicators(stats);
        
        // Update alert badges
        this.updateAlertBadges(stats);
    },
    
    /**
     * Update change percentage indicators
     */
    updateChangeIndicators(stats) {
        if (stats.payments_change !== undefined) {
            const paymentsChangeElement = DOM.elements.paymentsChange;
            if (paymentsChangeElement) {
                const change = stats.payments_change || 0;
                const changeClass = change >= 0 ? 'change-positive' : 'change-negative';
                const icon = change >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
                
                DOM.safeUpdateHTML(paymentsChangeElement, `
                    <i class="fas ${icon}"></i>
                    <span>${Formatters.formatChange(change)}</span>
                `);
                paymentsChangeElement.className = `stat-change ${changeClass}`;
            }
        }
        
        if (stats.users_change !== undefined) {
            const usersChangeElement = DOM.elements.usersChange;
            if (usersChangeElement) {
                const change = stats.users_change || 0;
                const changeClass = change >= 0 ? 'change-positive' : 'change-negative';
                const icon = change >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
                
                DOM.safeUpdateHTML(usersChangeElement, `
                    <i class="fas ${icon}"></i>
                    <span>${Formatters.formatChange(change)}</span>
                `);
                usersChangeElement.className = `stat-change ${changeClass}`;
            }
        }
    },
    
    /**
     * Update alert badges in navigation
     */
    updateAlertBadges(stats) {
        // Pending payments badge
        if (DOM.elements.pendingPaymentsBadge && stats.pending_payments) {
            DOM.safeUpdateText(DOM.elements.pendingPaymentsBadge, 
                stats.pending_payments > 99 ? '99+' : stats.pending_payments.toString());
        }
        
        // Pending bonuses badge
        if (DOM.elements.pendingBonusesBadge && stats.pending_bonus_count) {
            DOM.safeUpdateText(DOM.elements.pendingBonusesBadge, 
                stats.pending_bonus_count > 99 ? '99+' : stats.pending_bonus_count.toString());
        }
    },
    
    /**
     * Update payment status overview
     */
    updatePaymentStatus(data) {
        if (!data || !data.payment_status) return;
        
        const status = data.payment_status;
        
        DOM.safeUpdateText(DOM.elements.successfulPayments, Formatters.formatNumber(status.successful?.count || 0));
        DOM.safeUpdateText(DOM.elements.successfulAmount, Formatters.formatCurrency(status.successful?.amount || 0));
        
        DOM.safeUpdateText(DOM.elements.pendingPaymentsCount, Formatters.formatNumber(status.pending?.count || 0));
        DOM.safeUpdateText(DOM.elements.pendingAmount, Formatters.formatCurrency(status.pending?.amount || 0));
        
        DOM.safeUpdateText(DOM.elements.failedPayments, Formatters.formatNumber(status.failed?.count || 0));
        DOM.safeUpdateText(DOM.elements.failedAmount, Formatters.formatCurrency(status.failed?.amount || 0));
        
        DOM.safeUpdateText(DOM.elements.declinedPayments, Formatters.formatNumber(status.declined?.count || 0));
        DOM.safeUpdateText(DOM.elements.declinedAmount, Formatters.formatCurrency(status.declined?.amount || 0));
        
        DOM.safeUpdateText(DOM.elements.cancelledPayments, Formatters.formatNumber(status.cancelled?.count || 0));
        DOM.safeUpdateText(DOM.elements.cancelledAmount, Formatters.formatCurrency(status.cancelled?.amount || 0));
    },
    
    /**
     * Update recent payments table
     */
    updateRecentPayments(data) {
        if (!data || !data.recent_payments || !DOM.elements.paymentsTableBody) return;
        
        const payments = data.recent_payments;
        
        if (payments.length === 0) {
            DOM.elements.paymentsTableBody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; color: var(--neutral); padding: 2rem;">
                        <i class="fas fa-receipt" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
                        No recent payments
                    </td>
                </tr>
            `;
            return;
        }
        
        const rows = payments.map(payment => `
            <tr>
                <td>
                    <div style="font-weight: 600;">${this.escapeHTML(payment.user_name || 'N/A')}</div>
                    <div style="font-size: 0.8rem; color: var(--neutral);">${this.escapeHTML(payment.user_email || '')}</div>
                </td>
                <td style="font-weight: 700;">${Formatters.formatCurrency(payment.amount)}</td>
                <td>${Formatters.getStatusBadge(payment.status, payment.amount)}</td>
                <td style="font-size: 0.9rem; color: var(--neutral);">
                    ${Formatters.formatDate(payment.created_at)}
                </td>
            </tr>
        `).join('');
        
        DOM.elements.paymentsTableBody.innerHTML = rows;
    },
    
    /**
     * Update chart data (placeholder for chart library integration)
     */
    updateCharts(data) {
        if (!data || !data.charts) return;
        
        const charts = data.charts;
        
        // Users growth chart placeholder
        if (DOM.elements.usersChart && charts.users_growth) {
            // In a real implementation, this would initialize/update a chart library
            console.log('Users growth data:', charts.users_growth);
            // Example: ChartJS.updateChart('usersChart', charts.users_growth);
        }
        
        // Investment trends chart placeholder
        if (DOM.elements.investmentsChart && charts.investment_trends) {
            console.log('Investment trends data:', charts.investment_trends);
            // Example: ChartJS.updateChart('investmentsChart', charts.investment_trends);
        }
    },
    
    /**
     * HTML escape utility for safe content rendering
     */
    escapeHTML(str) {
        if (typeof str !== 'string') return '';
        
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },
    
    /**
     * Show loading state
     */
    showLoading() {
        document.body.style.cursor = 'wait';
        // Add loading indicators to critical sections
        this.addLoadingPlaceholders();
    },
    
    /**
     * Hide loading state
     */
    hideLoading() {
        document.body.style.cursor = 'default';
        this.removeLoadingPlaceholders();
    },
    
    /**
     * Add loading placeholders
     */
    addLoadingPlaceholders() {
        const loadingElements = [
            DOM.elements.totalPayments, DOM.elements.totalUsers, DOM.elements.activeUsers,
            DOM.elements.totalBonus, DOM.elements.pendingBonus, DOM.elements.pendingPayments
        ];
        
        loadingElements.forEach(element => {
            if (element) {
                element.classList.add('loading');
            }
        });
    },
    
    /**
     * Remove loading placeholders
     */
    removeLoadingPlaceholders() {
        const loadingElements = document.querySelectorAll('.loading');
        loadingElements.forEach(element => {
            element.classList.remove('loading');
        });
    },
    
    /**
     * Show error message
     */
    showError(message) {
        // Create or update error notification
        let errorDiv = document.getElementById('dashboard-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'dashboard-error';
            errorDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #f44336;
                color: white;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 1000;
                max-width: 400px;
                animation: slideInRight 0.3s ease-out;
            `;
            document.body.appendChild(errorDiv);
        }
        
        errorDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${this.escapeHTML(message)}</span>
            </div>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: white; margin-left: 1rem; cursor: pointer;">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv && errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 5000);
    },
    
    /**
     * Show success message
     */
    showSuccess(message) {
        let successDiv = document.getElementById('dashboard-success');
        if (!successDiv) {
            successDiv = document.createElement('div');
            successDiv.id = 'dashboard-success';
            successDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #4caf50;
                color: white;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 1000;
                max-width: 400px;
                animation: slideInRight 0.3s ease-out;
            `;
            document.body.appendChild(successDiv);
        }
        
        successDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas fa-check-circle"></i>
                <span>${this.escapeHTML(message)}</span>
            </div>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: white; margin-left: 1rem; cursor: pointer;">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        setTimeout(() => {
            if (successDiv && successDiv.parentElement) {
                successDiv.remove();
            }
        }, 3000);
    }
};

// Event Handlers and User Interactions
const EventManager = {
    /**
     * Initialize all event listeners
     */
    init() {
        this.initSearch();
        this.initNavigation();
        this.initQuickActions();
        this.initRefreshInterval();
    },
    
    /**
     * Initialize search functionality with debouncing
     */
    initSearch() {
        if (!DOM.elements.adminSearchInput) return;
        
        let searchTimeout;
        
        DOM.elements.adminSearchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            searchTimeout = setTimeout(() => {
                this.handleSearch(query);
            }, CONFIG.DEBOUNCE_DELAY);
        });
        
        // Handle Enter key
        DOM.elements.adminSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                clearTimeout(searchTimeout);
                this.handleSearch(e.target.value.trim());
            }
        });
    },
    
    /**
     * Handle user search
     */
    async handleSearch(query) {
        if (query.length < 2) return;
        
        try {
            const results = await APIService.searchUsers(query);
            this.displaySearchResults(results);
        } catch (error) {
            UIManager.showError(error.message);
        }
    },
    
    /**
     * Display search results (to be implemented based on UI requirements)
     */
    displaySearchResults(results) {
        console.log('Search results:', results);
        // Implementation depends on how you want to display search results
        // Could be a dropdown, modal, or redirect to users page
    },
    
    /**
     * Initialize navigation event handlers
     */
    initNavigation() {
        const navItems = [
            DOM.elements.navDashboard,
            DOM.elements.navUsers,
            DOM.elements.navPayments,
            DOM.elements.navBonuses,
            DOM.elements.navReports,
            DOM.elements.navSettings,
            DOM.elements.navLogout
        ].filter(item => item !== null);
        
        navItems.forEach(navItem => {
            navItem.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleNavigation(navItem.id);
            });
        });
    },
    
    /**
     * Handle navigation clicks
     */
    handleNavigation(navId) {
        const viewMap = {
            'nav-dashboard': 'dashboard',
            'nav-users': 'users',
            'nav-payments': 'payments',
            'nav-bonuses': 'bonuses',
            'nav-reports': 'reports',
            'nav-settings': 'settings',
            'nav-logout': 'logout'
        };
        
        const view = viewMap[navId];
        
        if (view === 'logout') {
            this.handleLogout();
            return;
        }
        
        AppState.currentView = view;
        this.updateActiveNav(navId);
        
        // In a full SPA, this would load different views
        // For now, we'll just update the active state
        console.log(`Navigating to: ${view}`);
    },
    
    /**
     * Update active navigation state
     */
    updateActiveNav(activeNavId) {
        // Remove active class from all nav items
        document.querySelectorAll('.nav-link').forEach(nav => {
            nav.classList.remove('active');
        });
        
        // Add active class to clicked nav item
        const activeNav = document.getElementById(activeNavId);
        if (activeNav) {
            activeNav.classList.add('active');
        }
    },
    
    /**
     * Handle logout
     */
    handleLogout() {
        if (confirm('Are you sure you want to logout?')) {
            window.location.href = '/admin/logout';
        }
    },
    
    /**
     * Initialize quick action buttons
     */
    initQuickActions() {
        const actions = [
            DOM.elements.actionAddUser,
            DOM.elements.actionProcessBonus,
            DOM.elements.actionManualPayment,
            DOM.elements.actionGenerateReport,
            DOM.elements.actionSystemBackup,
            DOM.elements.actionBulkActions
        ].filter(action => action !== null);
        
        actions.forEach(action => {
            action.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleQuickAction(action.id);
            });
        });
    },
    
    /**
     * Handle quick action clicks
     */
    handleQuickAction(actionId) {
        const actionMap = {
            'action-add-user': () => this.openUserModal(),
            'action-process-bonus': () => this.processBonus(),
            'action-manual-payment': () => this.manualPayment(),
            'action-generate-report': () => this.generateReport(),
            'action-system-backup': () => this.systemBackup(),
            'action-bulk-actions': () => this.bulkActions()
        };
        
        const action = actionMap[actionId];
        if (action) {
            action();
        }
    },
    
    /**
     * Quick action handlers (stubs for implementation)
     */
    openUserModal() {
        UIManager.showSuccess('Add User feature would open here');
        console.log('Opening add user modal');
    },
    
    processBonus() {
        UIManager.showSuccess('Bonus processing would start here');
        console.log('Processing bonuses');
    },
    
    manualPayment() {
        UIManager.showSuccess('Manual payment feature would open here');
        console.log('Opening manual payment');
    },
    
    generateReport() {
        UIManager.showSuccess('Report generation started');
        console.log('Generating report');
    },
    
    systemBackup() {
        UIManager.showSuccess('System backup initiated');
        console.log('Starting system backup');
    },
    
    bulkActions() {
        UIManager.showSuccess('Bulk actions modal would open here');
        console.log('Opening bulk actions');
    },
    
    /**
     * Initialize auto-refresh interval
     */
    initRefreshInterval() {
        setInterval(() => {
            if (AppState.currentView === 'dashboard') {
                DashboardManager.loadData();
            }
        }, CONFIG.REFRESH_INTERVAL);
    }
};

// Main Dashboard Manager
const DashboardManager = {
    /**
     * Initialize the dashboard
     */
    async init() {
        try {
            // Initialize DOM references
            DOM.init();
            
            // Initialize event handlers
            EventManager.init();
            
            // Load initial data
            await this.loadData();
            
            // Set up periodic refresh
            this.setupAutoRefresh();
            
            console.log('Admin dashboard initialized successfully');
            // 
             updateDashboard();
            
        } catch (error) {
            console.error('Dashboard initialization failed:', error);
            UIManager.showError('Failed to initialize dashboard. Please refresh the page.');
        }
    },
    
    /**
     * Load dashboard data from API
     */
    async loadData() {
        if (AppState.isLoading) return;
        
        try {
            AppState.isLoading = true;
            UIManager.showLoading();
            
            const data = await APIService.fetchAdminData();
            
            // Update application state
            AppState.adminData = data;
            AppState.lastUpdate = new Date();
            
            // Update UI with new data
            this.updateUI(data);
            
            UIManager.showSuccess('Dashboard updated successfully');
            
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            UIManager.showError(error.message || 'Failed to load dashboard data');
            
        } finally {
            AppState.isLoading = false;
            UIManager.hideLoading();
        }
    },
    
    /**
     * Update all UI components with new data
     */
    updateUI(data) {
        UIManager.updateStats(data);
        UIManager.updatePaymentStatus(data);
        UIManager.updateRecentPayments(data);
        UIManager.updateCharts(data);
        
        // Update last refresh time if element exists
        const lastUpdateElement = document.getElementById('last-update-time');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = new Date().toLocaleTimeString();
        }
    },
    
    /**
     * Set up automatic data refresh
     */
    setupAutoRefresh() {
        // Refresh on visibility change (when tab becomes active)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && AppState.currentView === 'dashboard') {
                this.loadData();
            }
        });
        
        // Manual refresh button (if added to HTML)
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }
    },
    
    /**
     * Force refresh dashboard data
     */
    forceRefresh() {
        this.loadData();
    }
};

// Application Bootstrap
document.addEventListener('DOMContentLoaded', function() {
    // Start the application
    DashboardManager.init();
    
    // Global error handler for uncaught errors
    window.addEventListener('error', function(event) {
        console.error('Global error:', event.error);
        UIManager.showError('An unexpected error occurred');
    });
    
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        UIManager.showError('An unexpected error occurred');
    });
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        DashboardManager,
        APIService,
        UIManager,
        Formatters
    };
}
