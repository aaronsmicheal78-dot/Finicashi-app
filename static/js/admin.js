class AdminDashboard {
    constructor() {
        this.currentSection = 'dashboard';
        this.adminData = null;
        this.dashboardMetrics = null;
        this.init();
    }

    async init() {
        await this.loadAdminData();
        this.initializeEventListeners();
        this.renderDashboard();
        this.startLiveUpdates();
    }

    // Unified API fetcher with error handling
    async apiFetch(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin', // ensures session cookies are sent
            ...options
        };

        try {
            const response = await fetch(url, defaultOptions);

            // Handle non-JSON or network errors
            if (!response.ok) {
                let message = `Request failed: ${response.status} ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    message = errorData.message || errorData.error || message;
                } catch (e) {
                    // Response not JSON—keep default message
                }
                throw new Error(message);
            }

            // Handle JSON parsing
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                throw new Error('Invalid response: expected JSON');
            }
        } catch (error) {
            console.error(`API Error (${url}):`, error);
            this.showNotification(`Error: ${error.message}`, 'error');
            return null;
        }
    }

    showNotification(message, type = 'info') {
        // Create or reuse a toast container
        let toastContainer = document.getElementById('admin-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'admin-toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                max-width: 400px;
            `;
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement('div');
        toast.className = `admin-toast admin-toast-${type}`;
        toast.style.cssText = `
            background: ${type === 'error' ? '#fee' : type === 'success' ? '#efe' : '#eef'};
            color: ${type === 'error' ? '#c33' : type === 'success' ? '#282' : '#228'};
            border-left: 4px solid ${type === 'error' ? '#c33' : type === 'success' ? '#282' : '#258'};
            padding: 12px 16px;
            margin-bottom: 10px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            animation: fadeIn 0.3s;
        `;
        toast.innerHTML = `<strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${message}`;

        toastContainer.appendChild(toast);

        // Auto-remove after 5s
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.5s';
            setTimeout(() => toast.remove(), 500);
        }, 5000);
    }

    // --- Data Loading ---
    async loadAdminData() {
        const adminData = localStorage.getItem('fincashpro_admin_data');
        if (adminData) {
            try {
                this.adminData = JSON.parse(adminData);
                this.updateUserInfo();
            } catch (e) {
                console.warn('Invalid admin data in localStorage');
            }
        }
        await this.refreshAllData();
    }

    initializeEventListeners() {
        document.querySelectorAll('.admin-nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchSection(item.dataset.section);
            });
        });

        document.getElementById('admin-refresh-data')?.addEventListener('click', () => {
            this.refreshAllData();
        });

        // Modal close buttons
        ['payment', 'bonus', 'user', 'message', 'confirm'].forEach(type => {
            const btn = document.getElementById(`admin-close-${type}-modal`);
            btn?.addEventListener('click', () => this.closeModal(type));
        });

        document.getElementById('admin-user-menu')?.addEventListener('click', () => {
            this.showUserMenu();
        });
    }

    // --- Navigation ---
    switchSection(section) {
        this.currentSection = section;
        document.querySelectorAll('.admin-nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.section === section);
        });

        const titles = {
            'dashboard': 'Dashboard Overview',
            'payment-requests': 'Payment Requests',
            'bonus-requests': 'Bonus Requests',
            'user-management': 'User Management',
            'messages': 'User Messages',
            'reports': 'System Reports',
            'system': 'System Settings'
        };
        document.getElementById('admin-current-section').textContent = titles[section] || 'Admin Panel';

        this.renderSection(section);
    }

    renderSection(section) {
        const contentArea = document.getElementById('admin-dynamic-content');
        if (!contentArea) return;

        let html = '';
        switch (section) {
            case 'dashboard': html = this.renderDashboardContent(); break;
            case 'payment-requests': html = this.renderPaymentRequests(); break;
            case 'bonus-requests': html = this.renderBonusRequests(); break;
            case 'user-management': html = this.renderUserManagement(); break;
            case 'messages': html = this.renderMessages(); break;
            case 'reports': html = this.renderReports(); break;
            case 'system': html = this.renderSystemSettings(); break;
            default: html = '<p>Section not found</p>';
        }
        contentArea.innerHTML = html;
    }

    // --- Dashboard Rendering ---
    renderDashboard() {
        this.renderStatsGrid(); // Will be populated by updateStats()
        this.renderSection('dashboard');
    }

    renderStatsGrid(data = null) {
        const statsGrid = document.getElementById('admin-stats-grid');
        if (!statsGrid) return;

        if (!data) {
            statsGrid.innerHTML = `
                <div class="admin-stat-card loading">loading...</div>
                <div class="admin-stat-card loading">Loading...</div>
                <div class="admin-stat-card loading">Loading...</div>
                <div class="admin-stat-card loading">Loading...</div>
                <div class="admin-stat-card loading">Loading...</div>
                <div class="admin-stat-card loading">Loading...</div>
            `;
            return;
        }

        const stats = [
            { label: 'Total Users', value: data.total_users.toLocaleString(), type: 'users' },
            { label: 'Pending Payments', value: data.pending_payments.toLocaleString(), type: 'payments' },
            { label: 'Total Bonuses', value: `$${data.total_bonuses.toFixed(2)}`, type: 'bonuses' },
            { label: 'Total Volume', value: `$${data.total_balances.toFixed(2)}`, type: 'volume' },
            { label: 'New Users (24h)', value: data.new_users_24h.toLocaleString(), type: 'users' },
            { label: 'Failed Logins (24h)', value: data.failed_logins_24h.toLocaleString(), type: 'security' }
        ];

        statsGrid.innerHTML = stats.map(stat => `
            <div class="admin-stat-card ${stat.type}">
                <div class="admin-stat-value">${stat.value}</div>
                <div class="admin-stat-label">${stat.label}</div>
            </div>
        `).join('');
    }

    renderDashboardContent() {
        return `
            <div class="admin-content-section">
                <div class="admin-section-header">
                    <h3 class="admin-section-title">Recent Activity</h3>
                    <div class="admin-section-actions">
                        <button class="admin-action-btn view" id="view-all-activity">View All</button>
                    </div>
                </div>
                <div class="admin-section-body">
                    <p class="admin-no-data">Recent activity feed will appear here soon.</p>
                </div>
            </div>

            <div class="admin-content-section">
                <div class="admin-section-header">
                    <h3 class="admin-section-title">Quick Actions</h3>
                </div>
                <div class="admin-section-body">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                        <button class="admin-action-btn view" id="quick-view-payments">Review Payments</button>
                        <button class="admin-action-btn approve" id="quick-process-bonuses">Process Bonuses</button>
                        <button class="admin-action-btn edit" id="quick-user-search">Search Users</button>
                        <button class="admin-action-btn view" id="quick-generate-report">Generate Report</button>
                    </div>
                </div>
            </div>
        `;
    }

    // --- Other Section Templates (unchanged) ---
    renderPaymentRequests() {
        return `
            <div class="admin-content-section">
                <div class="admin-section-header">
                    <h3 class="admin-section-title">Pending Payment Requests</h3>
                    <div class="admin-section-actions">
                        <button class="admin-action-btn view" id="export-payments">Export</button>
                        <button class="admin-action-btn approve" id="bulk-approve-payments">Bulk Approve</button>
                    </div>
                </div>
                <div class="admin-section-body">
                    <p class="admin-no-data">Payment requests will load here.</p>
                </div>
            </div>
        `;
    }

    renderBonusRequests() {
        return `
            <div class="admin-content-section">
                <div class="admin-section-header">
                    <h3 class="admin-section-title">Pending Bonus Requests</h3>
                    <div class="admin-section-actions">
                        <button class="admin-action-btn view" id="export-bonuses">Export</button>
                        <button class="admin-action-btn approve" id="bulk-approve-bonuses">Bulk Approve</button>
                    </div>
                </div>
                <div class="admin-section-body">
                    <p class="admin-no-data">Bonus requests will load here.</p>
                </div>
            </div>
        `;
    }

    renderUserManagement() {
        return `
            <div class="admin-content-section">
                <div class="admin-section-header">
                    <h3 class="admin-section-title">User Management</h3>
                    <div class="admin-section-actions">
                        <input type="text" id="user-search-input" placeholder="Search users..." class="admin-form-input" style="width: 300px;">
                        <button class="admin-action-btn view" id="search-users">Search</button>
                    </div>
                </div>
                <div class="admin-section-body">
                    <p class="admin-no-data">User list will appear after search.</p>
                </div>
            </div>
        `;
    }

    renderMessages() {
        return `
            <div class="admin-content-section">
                <div class="admin-section-header">
                    <h3 class="admin-section-title">User Messages</h3>
                    <div class="admin-section-actions">
                        <button class="admin-action-btn view" id="mark-all-read">Mark All Read</button>
                    </div>
                </div>
                <div class="admin-section-body">
                    <p class="admin-no-data">Messages will load here.</p>
                </div>
            </div>
        `;
    }

    renderReports() {
        return `
            <div class="admin-content-section">
                <div class="admin-section-header">
                    <h3 class="admin-section-title">System Reports</h3>
                    <div class="admin-section-actions">
                        <button class="admin-action-btn view" id="generate-financial-report">Financial Report</button>
                        <button class="admin-action-btn view" id="generate-user-report">User Report</button>
                    </div>
                </div>
                <div class="admin-section-body">
                    <div id="reports-container">
                        <p>Generate reports using the buttons above.</p>
                    </div>
                </div>
            </div>
        `;
    }

    renderSystemSettings() {
        return `
            <div class="admin-content-section">
                <div class="admin-section-header">
                    <h3 class="admin-section-title">System Configuration</h3>
                </div>
                <div class="admin-section-body">
                    <form id="system-settings-form">
                        <div class="admin-form-group">
                            <label class="admin-form-label">System Maintenance Mode</label>
                            <select class="admin-form-select" id="maintenance-mode">
                                <option value="false">Disabled</option>
                                <option value="true">Enabled</option>
                            </select>
                        </div>
                        <div class="admin-form-group">
                            <label class="admin-form-label">Auto-approve Payments Under ($)</label>
                            <input type="number" step="0.01" class="admin-form-input" id="auto-approve-limit" placeholder="0.00">
                        </div>
                        <div class="admin-form-group">
                            <label class="admin-form-label">System Notification Email</label>
                            <input type="email" class="admin-form-input" id="notification-email" placeholder="admin@fincashpro.com">
                        </div>
                        <button type="submit" class="admin-action-btn approve">Save Settings</button>
                    </form>
                </div>
            </div>
        `;
    }

    // --- Data Refresh ---
    async refreshAllData() {
        await this.updateStats();
        // Later: await this.updatePaymentRequests(); etc.
    }

    async updateStats() {
        const metrics = await this.apiFetch('/admin/dashboard/data');
        if (metrics) {
            this.dashboardMetrics = metrics;
            this.renderStatsGrid(metrics);
        } else {
            this.renderStatsGrid(null); // show loading/error
        }
    }

    // --- Modals & Utils ---
    closeModal(type) {
        const modal = document.getElementById(`admin-${type}-modal`);
        if (modal) modal.classList.remove('show');
    }

    updateUserInfo() {
        if (this.adminData) {
            const usernameEl = document.getElementById('admin-username');
            const avatarEl = document.getElementById('admin-user-avatar');
            if (usernameEl) usernameEl.textContent = this.adminData.username;
            if (avatarEl) avatarEl.textContent = this.adminData.username.charAt(0).toUpperCase();
        }
    }

    showUserMenu() {
        // Implement dropdown logic if needed
        console.log('User menu toggled');
    }

    startLiveUpdates() {
        // Refresh stats every 30 seconds
        setInterval(() => {
            if (this.currentSection === 'dashboard') {
                this.updateStats();
            }
        }, 30000);
    }
}

// Inject CSS for toasts if not present
(function injectToastCSS() {
    if (document.getElementById('admin-toast-styles')) return;
    const style = document.createElement('style');
    style.id = 'admin-toast-styles';
    style.textContent = `
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes fadeOut { from { opacity: 1; transform: translateY(0); } to { opacity: 0; transform: translateY(-10px); } }
        .admin-toast { font-size: 14px; }
    `;
    document.head.appendChild(style);
})();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.adminDashboard = new AdminDashboard();
});




    async function fetchAdminData() {
        const valueEl = document.getElementById('total-users-value');
        const valueE2 = document.getElementById('total-users-active');
        if (!valueEl) return; // Exit if element not found

        // Show loading state
        valueEl.textContent = 'Loading...';
        valueEl.style.opacity = '0.7';

        try {
            const response = await fetch('/admin/data', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                credentials: 'same-origin' // Ensures session cookies are sent
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Update UI with real number (formatted)
            if (typeof data.total_users === 'number',
                typeof data.total_active_users === 'number'
            ) {
                valueEl.textContent = data.total_users.toLocaleString();
                valueEl.textContent = data.total_active_users.toLocaleString();
            } 
                else {
                throw new Error('Invalid data format');}
                
            

        } 
        
        catch (error) {
            console.error('Failed to load total users:', error);
            valueEl.textContent = 'Error';
            valueEl.style.color = '#e53e3e'; // Red for error
        } finally {
            valueEl.style.opacity = '1';
        }
    }

    // Fetch when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        fetchAdminData();
    });


















//  class AdminDashboard {
//             constructor() {
//                 this.currentSection = 'dashboard';
//                 this.adminData = null;
//                 this.init();
//             }

//             async init() {
//                 await this.loadAdminData();
//                 this.initializeEventListeners();
//                 this.renderDashboard();
//                 this.startLiveUpdates();
//             }

//             async loadAdminData() {
//                 // Load admin data from localStorage or API
//                 const adminData = localStorage.getItem('fincashpro_admin_data');
//                 if (adminData) {
//                     this.adminData = JSON.parse(adminData);
//                     this.updateUserInfo();
//                 }

//                 // Load initial dashboard data
//                 await this.refreshAllData();
//             }

//             initializeEventListeners() {
//                 // Navigation
//                 document.querySelectorAll('.admin-nav-item').forEach(item => {
//                     item.addEventListener('click', (e) => {
//                         e.preventDefault();
//                         this.switchSection(item.dataset.section);
//                     });
//                 });

//                 // Refresh button
//                 document.getElementById('admin-refresh-data').addEventListener('click', () => {
//                     this.refreshAllData();
//                 });

//                 // Modal close buttons
//                 document.getElementById('admin-close-payment-modal').addEventListener('click', () => this.closeModal('payment'));
//                 document.getElementById('admin-close-bonus-modal').addEventListener('click', () => this.closeModal('bonus'));
//                 document.getElementById('admin-close-user-modal').addEventListener('click', () => this.closeModal('user'));
//                 document.getElementById('admin-close-message-modal').addEventListener('click', () => this.closeModal('message'));
//                 document.getElementById('admin-close-confirm-modal').addEventListener('click', () => this.closeModal('confirm'));

//                 // User menu
//                 document.getElementById('admin-user-menu').addEventListener('click', () => {
//                     this.showUserMenu();
//                 });
//             }

//             switchSection(section) {
//                 this.currentSection = section;
                
//                 // Update active nav item
//                 document.querySelectorAll('.admin-nav-item').forEach(item => {
//                     item.classList.remove('active');
//                 });
//                 document.querySelector(`[data-section="${section}"]`).classList.add('active');

//                 // Update header title
//                 const titles = {
//                     'dashboard': 'Dashboard Overview',
//                     'payment-requests': 'Payment Requests',
//                     'bonus-requests': 'Bonus Requests',
//                     'user-management': 'User Management',
//                     'messages': 'User Messages',
//                     'reports': 'System Reports',
//                     'system': 'System Settings'
//                 };
//                 document.getElementById('admin-current-section').textContent = titles[section] || 'Admin Panel';

//                 // Render section content
//                 this.renderSection(section);
//             }

//             renderSection(section) {
//                 const contentArea = document.getElementById('admin-dynamic-content');
                
//                 switch(section) {
//                     case 'dashboard':
//                         contentArea.innerHTML = this.renderDashboardContent();
//                         break;
//                     case 'payment-requests':
//                         contentArea.innerHTML = this.renderPaymentRequests();
//                         break;
//                     case 'bonus-requests':
//                         contentArea.innerHTML = this.renderBonusRequests();
//                         break;
//                     case 'user-management':
//                         contentArea.innerHTML = this.renderUserManagement();
//                         break;
//                     case 'messages':
//                         contentArea.innerHTML = this.renderMessages();
//                         break;
//                     case 'reports':
//                         contentArea.innerHTML = this.renderReports();
//                         break;
//                     case 'system':
//                         contentArea.innerHTML = this.renderSystemSettings();
//                         break;
//                 }
//             }

//             renderDashboard() {
//                 this.renderStatsGrid();
//                 this.renderSection('dashboard');
//             }

//             renderStatsGrid() {
//                 const statsGrid = document.getElementById('admin-stats-grid');
                
//                 // This is dynamically populated from API
//                 const stats = [
//                     { label: 'Total Users', value: '', change: '', type: '' },
//                     { label: 'Pending Payments', value: '', change: '', type: '' },
//                     { label: 'Pending Bonuses', value: '', change: '', type: '' },
//                     { label: 'Total Volume', value: '', change: '', type: '' },
//                     { label: 'Active Sessions', value: '', change: '', type: '' },
//                     { label: 'System Health', value: '', change: '', type: '' }
//                 ];

//                 statsGrid.innerHTML = stats.map(stat => `
//                     <div class="admin-stat-card ${stat.type}">
//                         <div class="admin-stat-value">${stat.value}</div>
//                         <div class="admin-stat-label">${stat.label}</div>
//                         <div class="admin-stat-change ${stat.change.startsWith('+') ? 'positive' : 'negative'}">
//                             ${stat.change}
//                         </div>
//                     </div>
//                 `).join('');
//             }

//             renderDashboardContent() {
//                 return `
//                     <div class="admin-content-section">
//                         <div class="admin-section-header">
//                             <h3 class="admin-section-title">Recent Activity</h3>
//                             <div class="admin-section-actions">
//                                 <button class="admin-action-btn view" id="view-all-activity">View All</button>
//                             </div>
//                         </div>
//                         <div class="admin-section-body">
//                             <table class="admin-data-table">
//                                 <thead>
//                                     <tr>
//                                         <th>Time</th>
//                                         <th>User</th>
//                                         <th>Action</th>
//                                         <th>Details</th>
//                                         <th>Status</th>
//                                     </tr>
//                                 </thead>
//                                 <tbody id="recent-activity-body">
//                                     <!-- Dynamic content -->
//                                 </tbody>
//                             </table>
//                         </div>
//                     </div>

//                     <div class="admin-content-section">
//                         <div class="admin-section-header">
//                             <h3 class="admin-section-title">Quick Actions</h3>
//                         </div>
//                         <div class="admin-section-body">
//                             <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
//                                 <button class="admin-action-btn view" id="quick-view-payments">Review Payments</button>
//                                 <button class="admin-action-btn approve" id="quick-process-bonuses">Process Bonuses</button>
//                                 <button class="admin-action-btn edit" id="quick-user-search">Search Users</button>
//                                 <button class="admin-action-btn view" id="quick-generate-report">Generate Report</button>
//                             </div>
//                         </div>
//                     </div>
//                 `;
//             }

//             renderPaymentRequests() {
//                 return `
//                     <div class="admin-content-section">
//                         <div class="admin-section-header">
//                             <h3 class="admin-section-title">Pending Payment Requests</h3>
//                             <div class="admin-section-actions">
//                                 <button class="admin-action-btn view" id="export-payments">Export</button>
//                                 <button class="admin-action-btn approve" id="bulk-approve-payments">Bulk Approve</button>
//                             </div>
//                         </div>
//                         <div class="admin-section-body">
//                             <table class="admin-data-table">
//                                 <thead>
//                                     <tr>
//                                         <th><input type="checkbox" id="select-all-payments"></th>
//                                         <th>ID</th>
//                                         <th>User</th>
//                                         <th>Amount</th>
//                                         <th>Type</th>
//                                         <th>Requested</th>
//                                         <th>Status</th>
//                                         <th>Actions</th>
//                                     </tr>
//                                 </thead>
//                                 <tbody id="payment-requests-body">
//                                     <!-- Dynamic content -->
//                                 </tbody>
//                             </table>
//                         </div>
//                     </div>
//                 `;
//             }

//             renderBonusRequests() {
//                 return `
//                     <div class="admin-content-section">
//                         <div class="admin-section-header">
//                             <h3 class="admin-section-title">Pending Bonus Requests</h3>
//                             <div class="admin-section-actions">
//                                 <button class="admin-action-btn view" id="export-bonuses">Export</button>
//                                 <button class="admin-action-btn approve" id="bulk-approve-bonuses">Bulk Approve</button>
//                             </div>
//                         </div>
//                         <div class="admin-section-body">
//                             <table class="admin-data-table">
//                                 <thead>
//                                     <tr>
//                                         <th><input type="checkbox" id="select-all-bonuses"></th>
//                                         <th>ID</th>
//                                         <th>User</th>
//                                         <th>Bonus Type</th>
//                                         <th>Amount</th>
//                                         <th>Requested</th>
//                                         <th>Status</th>
//                                         <th>Actions</th>
//                                     </tr>
//                                 </thead>
//                                 <tbody id="bonus-requests-body">
//                                     <!-- Dynamic content -->
//                                 </tbody>
//                             </table>
//                         </div>
//                     </div>
//                 `;
//             }

//             renderUserManagement() {
//                 return `
//                     <div class="admin-content-section">
//                         <div class="admin-section-header">
//                             <h3 class="admin-section-title">User Management</h3>
//                             <div class="admin-section-actions">
//                                 <input type="text" id="user-search-input" placeholder="Search users..." class="admin-form-input" style="width: 300px;">
//                                 <button class="admin-action-btn view" id="search-users">Search</button>
//                             </div>
//                         </div>
//                         <div class="admin-section-body">
//                             <table class="admin-data-table">
//                                 <thead>
//                                     <tr>
//                                         <th>User ID</th>
//                                         <th>Username</th>
//                                         <th>Email</th>
//                                         <th>Phone</th>
//                                         <th>Balance</th>
//                                         <th>Status</th>
//                                         <th>Joined</th>
//                                         <th>Actions</th>
//                                     </tr>
//                                 </thead>
//                                 <tbody id="users-management-body">
//                                     <!-- Dynamic content -->
//                                 </tbody>
//                             </table>
//                         </div>
//                     </div>
//                 `;
//             }

//             renderMessages() {
//                 return `
//                     <div class="admin-content-section">
//                         <div class="admin-section-header">
//                             <h3 class="admin-section-title">User Messages</h3>
//                             <div class="admin-section-actions">
//                                 <button class="admin-action-btn view" id="mark-all-read">Mark All Read</button>
//                             </div>
//                         </div>
//                         <div class="admin-section-body">
//                             <table class="admin-data-table">
//                                 <thead>
//                                     <tr>
//                                         <th>From</th>
//                                         <th>Subject</th>
//                                         <th>Message</th>
//                                         <th>Received</th>
//                                         <th>Status</th>
//                                         <th>Actions</th>
//                                     </tr>
//                                 </thead>
//                                 <tbody id="user-messages-body">
//                                     <!-- Dynamic content -->
//                                 </tbody>
//                             </table>
//                         </div>
//                     </div>
//                 `;
//             }

//             renderReports() {
//                 return `
//                     <div class="admin-content-section">
//                         <div class="admin-section-header">
//                             <h3 class="admin-section-title">System Reports</h3>
//                             <div class="admin-section-actions">
//                                 <button class="admin-action-btn view" id="generate-financial-report">Financial Report</button>
//                                 <button class="admin-action-btn view" id="generate-user-report">User Report</button>
//                             </div>
//                         </div>
//                         <div class="admin-section-body">
//                             <div id="reports-container">
//                                 <!-- Reports will be generated here -->
//                             </div>
//                         </div>
//                     </div>
//                 `;
//             }

//             renderSystemSettings() {
//                 return `
//                     <div class="admin-content-section">
//                         <div class="admin-section-header">
//                             <h3 class="admin-section-title">System Configuration</h3>
//                         </div>
//                         <div class="admin-section-body">
//                             <form id="system-settings-form">
//                                 <div class="admin-form-group">
//                                     <label class="admin-form-label">System Maintenance Mode</label>
//                                     <select class="admin-form-select" id="maintenance-mode">
//                                         <option value="false">Disabled</option>
//                                         <option value="true">Enabled</option>
//                                     </select>
//                                 </div>
//                                 <div class="admin-form-group">
//                                     <label class="admin-form-label">Auto-approve Payments Under</label>
//                                     <input type="number" class="admin-form-input" id="auto-approve-limit" placeholder="0.00">
//                                 </div>
//                                 <div class="admin-form-group">
//                                     <label class="admin-form-label">System Notification Email</label>
//                                     <input type="email" class="admin-form-input" id="notification-email" placeholder="admin@fincashpro.com">
//                                 </div>
//                                 <button type="submit" class="admin-action-btn approve">Save Settings</button>
//                             </form>
//                         </div>
//                     </div>
//                 `;
//             }

//             async refreshAllData() {
//                 // Simulate API calls to refresh all data
//                 await this.updatePaymentRequests();
//                 await this.updateBonusRequests();
//                 await this.updateUserMessages();
//                 await this.updateStats();
//             }

//             async updatePaymentRequests() {
//                 // Simulate API call
//                 const payments = await this.fetchPaymentRequests();
//                 document.getElementById('pending-payments-count').textContent = payments.filter(p => p.status === 'pending').length;
                
//                 // Update table if on payment requests page
//                 if (this.currentSection === 'payment-requests') {
//                     this.renderPaymentRequestsTable(payments);
//                 }
//             }

//             async updateBonusRequests() {
//                 // Simulate API call
//                 const bonuses = await this.fetchBonusRequests();
//                 document.getElementById('pending-bonuses-count').textContent = bonuses.filter(b => b.status === 'pending').length;
                
//                 // Update table if on bonus requests page
//                 if (this.currentSection === 'bonus-requests') {
//                     this.renderBonusRequestsTable(bonuses);
//                 }
//             }

//             async updateUserMessages() {
//                 // Simulate API call
//                 const messages = await this.fetchUserMessages();
//                 document.getElementById('unread-messages-count').textContent = messages.filter(m => !m.read).length;
                
//                 // Update table if on messages page
//                 if (this.currentSection === 'messages') {
//                     this.renderMessagesTable(messages);
//                 }
//             }

//             async updateStats() {
//                 // Refresh stats grid
//                 this.renderStatsGrid();
//             }

//             // Mock API methods - replace with actual API calls
//             async fetchPaymentRequests() {
//                 return [
//                     { id: 'PAY001', user: 'john_doe', amount: 150.00, type: 'withdrawal', requested: '2024-01-15', status: 'pending' },
//                     { id: 'PAY002', user: 'jane_smith', amount: 75.50, type: 'deposit', requested: '2024-01-15', status: 'pending' },
//                     { id: 'PAY003', user: 'bob_wilson', amount: 200.00, type: 'withdrawal', requested: '2024-01-14', status: 'approved' }
//                 ];
//             }

//             async fetchBonusRequests() {
//                 return [
//                     { id: 'BON001', user: 'alice_brown', type: 'referral', amount: 25.00, requested: '2024-01-15', status: 'pending' },
//                     { id: 'BON002', user: 'charlie_green', type: 'welcome', amount: 10.00, requested: '2024-01-15', status: 'pending' }
//                 ];
//             }

//             async fetchUserMessages() {
//                 return [
//                     { id: 'MSG001', from: 'john_doe', subject: 'Account Issue', message: 'Having trouble with...', received: '2024-01-15', read: false },
//                     { id: 'MSG002', from: 'jane_smith', subject: 'Payment Question', message: 'When will my...', received: '2024-01-14', read: true }
//                 ];
//             }

//             showModal(type, data = null) {
//                 const modal = document.getElementById(`admin-${type}-modal`);
//                 modal.classList.add('show');
                
//                 if (data) {
//                     this.populateModal(type, data);
//                 }
//             }

//             closeModal(type) {
//                 const modal = document.getElementById(`admin-${type}-modal`);
//                 modal.classList.remove('show');
//             }

//             populateModal(type, data) {
//                 // This would populate modal with specific data
//                 // Implementation depends on modal type and data structure
//             }

//             updateUserInfo() {
//                 if (this.adminData) {
//                     document.getElementById('admin-username').textContent = this.adminData.username;
//                     document.getElementById('admin-user-avatar').textContent = this.adminData.username.charAt(0).toUpperCase();
//                 }
//             }

//             showUserMenu() {
//                 // Implement user menu dropdown
//                 console.log('Show user menu');
//             }

//             startLiveUpdates() {
//                 // Start WebSocket or polling for live updates
//                 setInterval(() => {
//                     this.refreshAllData();
//                 }, 30000); // Refresh every 30 seconds
//             }
//         }

//         // Initialize admin dashboard
//         document.addEventListener('DOMContentLoaded', () => {
//             new AdminDashboard();
//         });


        
// fetch('/admin/dashboard/data')
//   .then(res => res.json())
//   .then(data => {
//     document.getElementById('metrics').innerHTML = `
//       <p>Total Users: ${data.total_users}</p>
//       <p>New (24h): ${data.new_users_24h}</p>
//       <p>Total Balance: ${data.total_balances.toFixed(2)}</p>
//       <!-- etc. -->
//     `;
//     // Or feed into Chart.js, etc.
//   });