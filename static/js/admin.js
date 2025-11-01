 class AdminDashboard {
            constructor() {
                this.currentSection = 'dashboard';
                this.adminData = null;
                this.init();
            }

            async init() {
                await this.loadAdminData();
                this.initializeEventListeners();
                this.renderDashboard();
                this.startLiveUpdates();
            }

            async loadAdminData() {
                // Load admin data from localStorage or API
                const adminData = localStorage.getItem('fincashpro_admin_data');
                if (adminData) {
                    this.adminData = JSON.parse(adminData);
                    this.updateUserInfo();
                }

                // Load initial dashboard data
                await this.refreshAllData();
            }

            initializeEventListeners() {
                // Navigation
                document.querySelectorAll('.admin-nav-item').forEach(item => {
                    item.addEventListener('click', (e) => {
                        e.preventDefault();
                        this.switchSection(item.dataset.section);
                    });
                });

                // Refresh button
                document.getElementById('admin-refresh-data').addEventListener('click', () => {
                    this.refreshAllData();
                });

                // Modal close buttons
                document.getElementById('admin-close-payment-modal').addEventListener('click', () => this.closeModal('payment'));
                document.getElementById('admin-close-bonus-modal').addEventListener('click', () => this.closeModal('bonus'));
                document.getElementById('admin-close-user-modal').addEventListener('click', () => this.closeModal('user'));
                document.getElementById('admin-close-message-modal').addEventListener('click', () => this.closeModal('message'));
                document.getElementById('admin-close-confirm-modal').addEventListener('click', () => this.closeModal('confirm'));

                // User menu
                document.getElementById('admin-user-menu').addEventListener('click', () => {
                    this.showUserMenu();
                });
            }

            switchSection(section) {
                this.currentSection = section;
                
                // Update active nav item
                document.querySelectorAll('.admin-nav-item').forEach(item => {
                    item.classList.remove('active');
                });
                document.querySelector(`[data-section="${section}"]`).classList.add('active');

                // Update header title
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

                // Render section content
                this.renderSection(section);
            }

            renderSection(section) {
                const contentArea = document.getElementById('admin-dynamic-content');
                
                switch(section) {
                    case 'dashboard':
                        contentArea.innerHTML = this.renderDashboardContent();
                        break;
                    case 'payment-requests':
                        contentArea.innerHTML = this.renderPaymentRequests();
                        break;
                    case 'bonus-requests':
                        contentArea.innerHTML = this.renderBonusRequests();
                        break;
                    case 'user-management':
                        contentArea.innerHTML = this.renderUserManagement();
                        break;
                    case 'messages':
                        contentArea.innerHTML = this.renderMessages();
                        break;
                    case 'reports':
                        contentArea.innerHTML = this.renderReports();
                        break;
                    case 'system':
                        contentArea.innerHTML = this.renderSystemSettings();
                        break;
                }
            }

            renderDashboard() {
                this.renderStatsGrid();
                this.renderSection('dashboard');
            }

            renderStatsGrid() {
                const statsGrid = document.getElementById('admin-stats-grid');
                
                // This would be dynamically populated from API
                const stats = [
                    { label: 'Total Users', value: '12,458', change: '+2.5%', type: 'success' },
                    { label: 'Pending Payments', value: '47', change: '+5', type: 'warning' },
                    { label: 'Pending Bonuses', value: '23', change: '-3', type: 'danger' },
                    { label: 'Total Volume', value: '$2.4M', change: '+12.8%', type: 'success' },
                    { label: 'Active Sessions', value: '1,247', change: '+34', type: 'info' },
                    { label: 'System Health', value: '99.9%', change: '0%', type: 'success' }
                ];

                statsGrid.innerHTML = stats.map(stat => `
                    <div class="admin-stat-card ${stat.type}">
                        <div class="admin-stat-value">${stat.value}</div>
                        <div class="admin-stat-label">${stat.label}</div>
                        <div class="admin-stat-change ${stat.change.startsWith('+') ? 'positive' : 'negative'}">
                            ${stat.change}
                        </div>
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
                            <table class="admin-data-table">
                                <thead>
                                    <tr>
                                        <th>Time</th>
                                        <th>User</th>
                                        <th>Action</th>
                                        <th>Details</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody id="recent-activity-body">
                                    <!-- Dynamic content -->
                                </tbody>
                            </table>
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
                            <table class="admin-data-table">
                                <thead>
                                    <tr>
                                        <th><input type="checkbox" id="select-all-payments"></th>
                                        <th>ID</th>
                                        <th>User</th>
                                        <th>Amount</th>
                                        <th>Type</th>
                                        <th>Requested</th>
                                        <th>Status</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="payment-requests-body">
                                    <!-- Dynamic content -->
                                </tbody>
                            </table>
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
                            <table class="admin-data-table">
                                <thead>
                                    <tr>
                                        <th><input type="checkbox" id="select-all-bonuses"></th>
                                        <th>ID</th>
                                        <th>User</th>
                                        <th>Bonus Type</th>
                                        <th>Amount</th>
                                        <th>Requested</th>
                                        <th>Status</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="bonus-requests-body">
                                    <!-- Dynamic content -->
                                </tbody>
                            </table>
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
                            <table class="admin-data-table">
                                <thead>
                                    <tr>
                                        <th>User ID</th>
                                        <th>Username</th>
                                        <th>Email</th>
                                        <th>Phone</th>
                                        <th>Balance</th>
                                        <th>Status</th>
                                        <th>Joined</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="users-management-body">
                                    <!-- Dynamic content -->
                                </tbody>
                            </table>
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
                            <table class="admin-data-table">
                                <thead>
                                    <tr>
                                        <th>From</th>
                                        <th>Subject</th>
                                        <th>Message</th>
                                        <th>Received</th>
                                        <th>Status</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="user-messages-body">
                                    <!-- Dynamic content -->
                                </tbody>
                            </table>
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
                                <!-- Reports will be generated here -->
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
                                    <label class="admin-form-label">Auto-approve Payments Under</label>
                                    <input type="number" class="admin-form-input" id="auto-approve-limit" placeholder="0.00">
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

            async refreshAllData() {
                // Simulate API calls to refresh all data
                await this.updatePaymentRequests();
                await this.updateBonusRequests();
                await this.updateUserMessages();
                await this.updateStats();
            }

            async updatePaymentRequests() {
                // Simulate API call
                const payments = await this.fetchPaymentRequests();
                document.getElementById('pending-payments-count').textContent = payments.filter(p => p.status === 'pending').length;
                
                // Update table if on payment requests page
                if (this.currentSection === 'payment-requests') {
                    this.renderPaymentRequestsTable(payments);
                }
            }

            async updateBonusRequests() {
                // Simulate API call
                const bonuses = await this.fetchBonusRequests();
                document.getElementById('pending-bonuses-count').textContent = bonuses.filter(b => b.status === 'pending').length;
                
                // Update table if on bonus requests page
                if (this.currentSection === 'bonus-requests') {
                    this.renderBonusRequestsTable(bonuses);
                }
            }

            async updateUserMessages() {
                // Simulate API call
                const messages = await this.fetchUserMessages();
                document.getElementById('unread-messages-count').textContent = messages.filter(m => !m.read).length;
                
                // Update table if on messages page
                if (this.currentSection === 'messages') {
                    this.renderMessagesTable(messages);
                }
            }

            async updateStats() {
                // Refresh stats grid
                this.renderStatsGrid();
            }

            // Mock API methods - replace with actual API calls
            async fetchPaymentRequests() {
                return [
                    { id: 'PAY001', user: 'john_doe', amount: 150.00, type: 'withdrawal', requested: '2024-01-15', status: 'pending' },
                    { id: 'PAY002', user: 'jane_smith', amount: 75.50, type: 'deposit', requested: '2024-01-15', status: 'pending' },
                    { id: 'PAY003', user: 'bob_wilson', amount: 200.00, type: 'withdrawal', requested: '2024-01-14', status: 'approved' }
                ];
            }

            async fetchBonusRequests() {
                return [
                    { id: 'BON001', user: 'alice_brown', type: 'referral', amount: 25.00, requested: '2024-01-15', status: 'pending' },
                    { id: 'BON002', user: 'charlie_green', type: 'welcome', amount: 10.00, requested: '2024-01-15', status: 'pending' }
                ];
            }

            async fetchUserMessages() {
                return [
                    { id: 'MSG001', from: 'john_doe', subject: 'Account Issue', message: 'Having trouble with...', received: '2024-01-15', read: false },
                    { id: 'MSG002', from: 'jane_smith', subject: 'Payment Question', message: 'When will my...', received: '2024-01-14', read: true }
                ];
            }

            showModal(type, data = null) {
                const modal = document.getElementById(`admin-${type}-modal`);
                modal.classList.add('show');
                
                if (data) {
                    this.populateModal(type, data);
                }
            }

            closeModal(type) {
                const modal = document.getElementById(`admin-${type}-modal`);
                modal.classList.remove('show');
            }

            populateModal(type, data) {
                // This would populate modal with specific data
                // Implementation depends on modal type and data structure
            }

            updateUserInfo() {
                if (this.adminData) {
                    document.getElementById('admin-username').textContent = this.adminData.username;
                    document.getElementById('admin-user-avatar').textContent = this.adminData.username.charAt(0).toUpperCase();
                }
            }

            showUserMenu() {
                // Implement user menu dropdown
                console.log('Show user menu');
            }

            startLiveUpdates() {
                // Start WebSocket or polling for live updates
                setInterval(() => {
                    this.refreshAllData();
                }, 30000); // Refresh every 30 seconds
            }
        }

        // Initialize admin dashboard
        document.addEventListener('DOMContentLoaded', () => {
            new AdminDashboard();
        });