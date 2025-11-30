

   // Group Modal Functions
function openGroupModal(groupType) {
    const modal = document.getElementById(groupType + 'Modal');
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.querySelector('.group-modal').classList.add('active');
    }, 10);
}

function closeGroupModal(groupType) {
    const modal = document.getElementById(groupType + 'Modal');
    modal.querySelector('.group-modal').classList.remove('active');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 300);
}

function registerGroup(size) {
    // Redirect to registration page with group size parameter
    window.location.href = `/register?group_size=${size}`;
}

// Close modal when clicking outside
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('group-modal-overlay')) {
        const modals = document.querySelectorAll('.group-modal-overlay');
        modals.forEach(modal => {
            modal.querySelector('.group-modal').classList.remove('active');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
        });
    }
});
document.addEventListener("DOMContentLoaded", () => {
  // Fetch logged-in user data from API
  fetch("/user/profile")
    .then(res => {
      if (!res.ok) throw new Error("Unauthorized or error");
      return res.json();
    })
    .then(user => {
      console.log("User data:", user);
      console.log("Packages:", user.packages);
      
      // Helper function to format currency
      const formatCurrency = (amount) => {
        if (amount === undefined || amount === null) return '0';
        return new Intl.NumberFormat('en-UG').format(amount);
      };

      // Set user details
      document.getElementById("memberSince").textContent = user.memberSince ? new Date(user.memberSince).toLocaleDateString() : 'N/A';
      document.getElementById("isVerified").textContent = user.isVerified ? 'Yes' : 'No';
     // document.getElementById("isActive").textContent = user.isActive ? 'Active' : 'Inactive';
      document.getElementById("referralLink").value = user.referralLink || 'N/A';
      document.getElementById("username").textContent = user.username || 'N/A';
      document.getElementById('user-id').textContent = user.id || 'N/A';
      document.getElementById("email").textContent = user.email || 'N/A';
      document.getElementById("phone").textContent = user.phone || 'N/A';
      document.getElementById("referral_code").textContent = user.referralCode || 'N/A';
      
      // Format and set balance values
      document.getElementById("available-balance").textContent = formatCurrency(user.availableBalance);
      document.getElementById("actual-balance").textContent = formatCurrency(user.actualBalance);
      document.getElementById("bonus").textContent = formatCurrency(user.bonus);
      
      // Fix: Add referral bonus display (you mentioned this in HTML but not in JS)
      document.getElementById("referral-bonus").textContent = formatCurrency(user.referralBonus || 0);

      // Handle packages
      if (user.packages && user.packages.length > 0) {
        const packageNames = user.packages.map(pkg => pkg.name).join(', ');
        document.getElementById("package").textContent = packageNames;
      } else {
        document.getElementById("package").textContent = "No active package";
      }
    })
    .catch(error => {
      console.error("Error fetching user profile:", error);
      document.getElementById("package").textContent = "Error loading package";
    });
});

    // User Controls
    const UserControls = {
        init() {
            // Notification icon
            if (DOM.elements.notificationIcon) {
                DOM.elements.notificationIcon.addEventListener('click', () => {
                    this.showNotifications();
                });
            }
            
            // Settings icon
            if (DOM.elements.settingsIcon) {
                DOM.elements.settingsIcon.addEventListener('click', () => {
                    this.showSettings();
                });
            }
            
        
           
        },
        
        showNotifications() {
            UI.showMessage('Notifications feature coming soon!', 'info');
        },
        
        showSettings() {
            UI.showMessage('Settings feature coming soon!', 'info');
            },
        

    };


//================================================================================
// POLICY DOCUMENT JS
//==================================================================================
        // Add interactivity to policy navigation
        document.addEventListener('DOMContentLoaded', function() {
            const navItems = document.querySelectorAll('.policy-nav-item');
            
            navItems.forEach(item => {
                item.addEventListener('click', function() {
                    // Remove active class from all items
                    navItems.forEach(navItem => navItem.classList.remove('active'));
                    
                    // Add active class to clicked item
                    this.classList.add('active');
                    
                    // Get the target section ID
                    const targetId = this.getAttribute('data-target');
                    
                    // Scroll to the target section
                    const targetSection = document.getElementById(targetId);
                    if (targetSection) {
                        targetSection.scrollIntoView({ behavior: 'smooth' });
                    }
                });
            });
            
            // Highlight the active section based on scroll position
            window.addEventListener('scroll', function() {
                const sections = document.querySelectorAll('.policy-section');
                let current = '';
                
                sections.forEach(section => {
                    const sectionTop = section.offsetTop;
                    const sectionHeight = section.clientHeight;
                    if (scrollY >= (sectionTop - 150)) {
                        current = section.getAttribute('id');
                    }
                });
                
                navItems.forEach(item => {
                    item.classList.remove('active');
                    if (item.getAttribute('data-target') === current) {
                        item.classList.add('active');
                    }
                });
            });
        });
// });
document.addEventListener("DOMContentLoaded", () => {
    const waBtn = document.getElementById("share-whatsapp");
    const referralSpan = document.getElementById("referralLink");
    const copyBtn = document.getElementById("copy-link");

    // Copy button logic
    copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(referralSpan.textContent);
        copyBtn.textContent = "Copied!";
        setTimeout(() => copyBtn.textContent = "Copy", 1500);
    });

    // WhatsApp share logic
    waBtn.addEventListener("click", () => {
        const link = referralSpan.textContent;
        const message = encodeURIComponent(`Join Finicashi using my referral link: ${link}`);
        const whatsappURL = `https://wa.me/?text=${message}`;

        window.open(whatsappURL, "_blank");
    });
});
// Earnings Dashboard - Updated for referral stats and lifetime earnings
// Earnings Dashboard - Clean Version
class EarningsDashboard {
    constructor(options = {}) {
        this.apiBaseUrl = options.apiBaseUrl || '';
        this.refreshInterval = options.refreshInterval || 300000;
        this.elements = {};
        console.log("🎯 EarningsDashboard created");
        this.init();
    }

    init() {
        console.log("🔄 Initializing dashboard...");
        this.cacheElements();
        this.bindEvents();
        this.loadEarnings();
        
        if (this.refreshInterval > 0) {
            setInterval(() => this.loadEarnings(), this.refreshInterval);
        }
    }

    cacheElements() {
        console.log("🔍 Caching HTML elements...");
        
        // Main period elements
        this.elements.today = document.getElementById('earningsToday');
        this.elements.week = document.getElementById('earningsWeek');
        this.elements.month = document.getElementById('earningsMonth');
        
        // Breakdown elements
        this.elements.referralBonus = document.getElementById('referral-bonus');
        this.elements.signupBonus = document.getElementById('bonus');
        this.elements.availableBalance = document.getElementById('available-balance');
        this.elements.walletBalance = document.getElementById('wallet-balance');
        this.elements.activeReferrals = document.getElementById('total-direct-referrals');
        
        // Log what we found
        console.log("📊 Elements found:", {
            today: !!this.elements.today,
            week: !!this.elements.week,
            month: !!this.elements.month,
            referralBonus: !!this.elements.referralBonus,
            signupBonus: !!this.elements.signupBonus,
            availableBalance: !!this.elements.availableBalance,
            walletBalance: !!this.elements.walletBalance,
            activeReferrals: !!this.elements.activeReferrals
        });

        // Create error container if needed
        this.elements.errorContainer = document.getElementById('earnings-error') || this.createErrorContainer();
    }

    createErrorContainer() {
        const container = document.createElement('div');
        container.id = 'earnings-error';
        container.className = 'alert alert-danger';
        container.style.display = 'none';
        
        // Try to find a container to put the error in
        const mainContainer = document.querySelector('.container, main, body');
        if (mainContainer) {
            mainContainer.prepend(container);
        }
        
        return container;
    }

    bindEvents() {
        const refreshBtn = document.getElementById('refresh-earnings');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadEarnings());
        }
    }

    async loadEarnings() {
        console.log("📡 Fetching earnings data from API...");
        
        try {
            this.setLoadingState(true);
            this.hideError();

            const response = await fetch('/api/user/total-earnings', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                credentials: 'same-origin'
            });

            console.log("📨 API Response status:", response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("✅ API Data received:", data);
            
            if (data.error) {
                throw new Error(data.message || data.error);
            }

            this.updateDisplay(data);
            this.setLoadingState(false);
            console.log("🎉 Dashboard updated successfully!");

        } catch (error) {
            console.error('❌ Failed to load earnings:', error);
            this.showError(error.message);
            this.setLoadingState(false);
        }
    }

    updateDisplay(data) {
        console.log("🖥️ Updating display with data...");
        
        // Update period totals
        this.updateElement(this.elements.today, data.today);
        this.updateElement(this.elements.week, data.this_week);
        this.updateElement(this.elements.month, data.this_month);
        
        // Update breakdown
        if (data.breakdown) {
            this.updateElement(this.elements.referralBonus, data.breakdown.referral_bonus);
            this.updateElement(this.elements.signupBonus, data.breakdown.signup_bonus);
            this.updateElement(this.elements.availableBalance, data.breakdown.available_balance);
            this.updateElement(this.elements.walletBalance, data.breakdown.wallet_balance);
            this.updateElement(this.elements.activeReferrals, data.referral_stats.total_direct_referrals);
        }
    }

    updateElement(element, value) {
        if (!element) {
            console.log("⚠️ Element is null, cannot update");
            return;
        }
        
        try {
            const numericValue = parseFloat(value);
            if (isNaN(numericValue)) {
                element.textContent = '0.00';
                return;
            }
            
            element.textContent = this.formatCurrency(numericValue);
            console.log(`✅ Updated ${element.id} to: ${element.textContent}`);
        } catch (error) {
            console.error('Error updating element:', error);
            element.textContent = '0.00';
        }
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    setLoadingState(loading) {
        // Simple loading state - you can enhance this later
        Object.values(this.elements).forEach(element => {
            if (element && element.style) {
                element.style.opacity = loading ? '0.6' : '1';
            }
        });
    }

    showError(message) {
        console.error("💥 Showing error:", message);
        if (this.elements.errorContainer) {
            this.elements.errorContainer.textContent = `Error: ${message}`;
            this.elements.errorContainer.style.display = 'block';
        }
    }

    hideError() {
        if (this.elements.errorContainer) {
            this.elements.errorContainer.style.display = 'none';
        }
    }

    refresh() {
        this.loadEarnings();
    }
}

// Initialize when DOM is ready
console.log("🚀 Earnings dashboard script loaded, waiting for DOM...");

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log("📄 DOM Content Loaded - Initializing EarningsDashboard");
        window.earningsDashboard = new EarningsDashboard();
    });
} else {
    console.log("⚡ DOM already ready - Initializing EarningsDashboard immediately");
    window.earningsDashboard = new EarningsDashboard();
}


  // Policy Document Toggle
        document.addEventListener('DOMContentLoaded', function() {
            const policyToggle = document.getElementById('policyToggle');
            const policyContainer = document.getElementById('policyContainer');
            
            policyToggle.addEventListener('click', function() {
                policyContainer.classList.toggle('active');
                
                if (policyContainer.classList.contains('active')) {
                    this.innerHTML = '<i class="fas fa-times"></i> Hide Policy Document';
                } else {
                    this.innerHTML = '<i class="fas fa-file-alt"></i> View Policy Document';
                }
            });
            
            // Add interactivity to policy navigation
            const navItems = document.querySelectorAll('.policy-nav-item');
            
            navItems.forEach(item => {
                item.addEventListener('click', function() {
                    // Remove active class from all items
                    navItems.forEach(navItem => navItem.classList.remove('active'));
                    
                    // Add active class to clicked item
                    this.classList.add('active');
                    
                    // Get the target section ID
                    const targetId = this.getAttribute('data-target');
                    
                    // Scroll to the target section
                    const targetSection = document.getElementById(targetId);
                    if (targetSection) {
                        targetSection.scrollIntoView({ behavior: 'smooth' });
                    }
                });
            });
            
            // Highlight the active section based on scroll position
            window.addEventListener('scroll', function() {
                const sections = document.querySelectorAll('.policy-section');
                let current = '';
                
                sections.forEach(section => {
                    const sectionTop = section.offsetTop;
                    const sectionHeight = section.clientHeight;
                    if (scrollY >= (sectionTop - 150)) {
                        current = section.getAttribute('id');
                    }
                });
                
                navItems.forEach(item => {
                    item.classList.remove('active');
                    if (item.getAttribute('data-target') === current) {
                        item.classList.add('active');
                    }
                });
            });
        });
// MODALS (QUEENS AND AMBASSADORS REGISTRATION JS)
    // Close when clicking outside modal content

// Logout handler with server-side session clearing
document.getElementById("log-out").onclick = async () => {
    if (!confirm("Are you sure you want to logout?")) return;
    
    try {
        // Call your logout API endpoint first
        const response = await fetch("/api/logout", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });
        
        if (response.ok) {
            // Redirect to login page after successful logout
            window.location.href = "/";
        } else {
            alert("Logout failed. Please try again.");
        }
    } catch (error) {
        console.error("Logout error:", error);
        // Fallback: redirect anyway
        window.location.href = "/index";
    }
};
    // copying referral link
document.getElementById("copyRefBtn").addEventListener("click", () => {
  const referralLinkInput = document.getElementById("referralLink");

  // Select the input text
  referralLinkInput.select();
  referralLinkInput.setSelectionRange(0, 99999); // for mobile

  // Copy to clipboard
  navigator.clipboard.writeText(referralLinkInput.value)
    .then(() => {
      // Change button text temporarily
      const btn = document.getElementById("copyRefBtn");
      const originalText = btn.innerHTML;
      btn.innerHTML = "Copied!";
      setTimeout(() => {
        btn.innerHTML = originalText;
      }, 1500); // revert after 1.5 seconds
    })
    .catch(err => {
      console.error("Failed to copy: ", err);
    });
});

// Recent Activity

// =============================================
// RECENT ACTIVITY MANAGER - Production Ready
// =============================================

class RecentActivityManager {
    constructor() {
        this.config = {
            apiEndpoint: '/api/recent_activity',
            refreshInterval: 60000, // 1 minute
            maxRetries: 3,
            pageSize: 20,
            cacheDuration: 30000 // 30 seconds
        };
        
        this.elements = {
            list: document.getElementById('recentActivityList'),
            loadingMsg: document.getElementById('activityLoadingMsg'),
            emptyMsg: document.getElementById('activityEmptyMsg'),
            template: document.getElementById('activityItemTemplate')
        };
        
        this.state = {
            isLoading: false,
            lastUpdate: null,
            currentPage: 1,
            hasMore: false,
            activities: [],
            cache: null,
            cacheTimestamp: null
        };
        
        this.activityStyles = {
            bonus: {
                icon: 'fa-gift',
                color: 'text-success',
                prefix: '+',
                bgColor: 'bg-success-light'
            },
            deposit: {
                icon: 'fa-arrow-down',
                color: 'text-info',
                prefix: '+',
                bgColor: 'bg-info-light'
            },
            withdraw: {
                icon: 'fa-arrow-up',
                color: 'text-warning',
                prefix: '-',
                bgColor: 'bg-warning-light'
            }
        };
        
        this.init();
    }

    // =============================================
    // INITIALIZATION
    // =============================================

    init() {
        if (!this.validateElements()) {
            console.error('Required DOM elements not found');
            return;
        }
        
        this.bindEvents();
        this.loadActivities();
        this.startAutoRefresh();
    }

    validateElements() {
        const required = ['list', 'loadingMsg', 'emptyMsg'];
        return required.every(id => this.elements[id] !== null);
    }

    bindEvents() {
        // Scroll loading for infinite scroll
        window.addEventListener('scroll', this.handleScroll.bind(this));
        
        // Refresh on visibility change
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.shouldRefresh()) {
                this.loadActivities();
            }
        });
    }

    // =============================================
    // DATA FETCHING & CACHING
    // =============================================

    async loadActivities(page = 1, useCache = true) {
        if (this.state.isLoading) return;
        
        // Check cache
        if (useCache && this.isCacheValid()) {
            this.renderFromCache();
            return;
        }
        
        this.setLoadingState(true);
        
        try {
            const url = `${this.config.apiEndpoint}?page=${page}&page_size=${this.config.pageSize}`;
            const response = await this.fetchWithRetry(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            await this.handleDataResponse(data, page);
            
        } catch (error) {
            this.handleError(error);
        } finally {
            this.setLoadingState(false);
        }
    }

    async fetchWithRetry(url, retries = this.config.maxRetries) {
        for (let attempt = 1; attempt <= retries; attempt++) {
            try {
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'Cache-Control': 'no-cache'
                    }
                });
                
                if (response.ok) return response;
                
                if (attempt === retries) {
                    throw new Error(`Failed after ${retries} attempts`);
                }
                
                // Exponential backoff
                await this.delay(Math.pow(2, attempt) * 1000);
                
            } catch (error) {
                if (attempt === retries) throw error;
                await this.delay(Math.pow(2, attempt) * 1000);
            }
        }
    }

    async handleDataResponse(data, page) {
        // Validate response structure
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid response format');
        }
        
        const activities = data.activities || [];
        const pagination = data.pagination || {};
        
        // Update state
        this.state.currentPage = page;
        this.state.hasMore = pagination.has_next || false;
        this.state.lastUpdate = new Date();
        
        if (page === 1) {
            this.state.activities = activities;
        } else {
            this.state.activities = [...this.state.activities, ...activities];
        }
        
        // Cache the data
        this.updateCache(data);
        
        // Render UI
        this.renderActivities();
        
        // Update empty state
        this.updateEmptyState(activities.length === 0 && page === 1);
        
        // Dispatch custom event for other components
        this.dispatchActivityUpdateEvent(activities.length);
    }

    // =============================================
    // CACHE MANAGEMENT
    // =============================================

    updateCache(data) {
        this.state.cache = data;
        this.state.cacheTimestamp = Date.now();
    }

    isCacheValid() {
        if (!this.state.cache || !this.state.cacheTimestamp) return false;
        
        const cacheAge = Date.now() - this.state.cacheTimestamp;
        return cacheAge < this.config.cacheDuration;
    }

    renderFromCache() {
        if (this.state.cache) {
            this.state.activities = this.state.cache.activities || [];
            this.renderActivities();
            this.updateEmptyState(this.state.activities.length === 0);
        }
    }

    shouldRefresh() {
        if (!this.state.lastUpdate) return true;
        
        const timeSinceLastUpdate = Date.now() - this.state.lastUpdate.getTime();
        return timeSinceLastUpdate > this.config.refreshInterval;
    }

    // =============================================
    // RENDERING ENGINE
    // =============================================

    renderActivities() {
        if (!this.state.activities.length) {
            this.elements.list.innerHTML = '';
            return;
        }
        
        const fragment = document.createDocumentFragment();
        
        this.state.activities.forEach(activity => {
            const activityElement = this.createActivityElement(activity);
            if (activityElement) {
                fragment.appendChild(activityElement);
            }
        });
        
        // Clear and update
        this.elements.list.innerHTML = '';
        this.elements.list.appendChild(fragment);
        
        // Add animation
        this.animateNewActivities();
    }

    createActivityElement(activity) {
        // Use template if available, otherwise create manually
        if (this.elements.template) {
            try {
                const template = this.elements.template.content.cloneNode(true);
                const activityItem = template.querySelector('.activity-item');
                const icon = template.querySelector('.activity-icon i');
                const title = template.querySelector('.activity-title');
                const time = template.querySelector('.activity-time');
                const amount = template.querySelector('.activity-amount');
                
                if (activityItem) {
                    const style = this.activityStyles[activity.type] || this.activityStyles.deposit;
                    
                    activityItem.setAttribute('data-type', activity.type);
                    activityItem.classList.add('activity-item--animated');
                    
                    icon.className = `fas ${style.icon}`;
                    title.textContent = activity.title || 'Transaction';
                    time.textContent = this.formatTimestamp(activity.timestamp);
                    amount.textContent = this.formatAmount(activity, style);
                    amount.className = `activity-amount ${style.color}`;
                    
                    if (style.bgColor) {
                        activityItem.classList.add(style.bgColor);
                    }
                    
                    return activityItem;
                }
            } catch (error) {
                console.error('Error creating activity from template:', error);
            }
        }
        
        // Fallback: create element manually
        return this.createFallbackActivityElement(activity);
    }

    createFallbackActivityElement(activity) {
        const style = this.activityStyles[activity.type] || this.activityStyles.deposit;
        
        const li = document.createElement('li');
        li.className = `activity-item activity-item--animated`;
        li.setAttribute('data-type', activity.type);
        
        li.innerHTML = `
            <div class="activity-icon">
                <i class="fas ${style.icon}"></i>
            </div>
            <div class="activity-details">
                <div class="activity-title">${this.escapeHtml(activity.title || 'Transaction')}</div>
                <div class="activity-time">${this.formatTimestamp(activity.timestamp)}</div>
            </div>
            <div class="activity-amount ${style.color}">
                ${this.formatAmount(activity, style)}
            </div>
        `;
        
        if (style.bgColor) {
            li.classList.add(style.bgColor);
        }
        
        return li;
    }

    // =============================================
    // FORMATTING UTILITIES
    // =============================================

    formatTimestamp(timestamp) {
        if (!timestamp) return 'Recently';
        
        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return 'Recently';
            
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);
            
            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            
            return date.toLocaleDateString();
            
        } catch (error) {
            return 'Recently';
        }
    }

    formatAmount(activity, style) {
        const amount = activity.amount || 0;
        const currency = activity.currency || 'UGX';
        const formattedAmount = typeof amount === 'number' 
            ? amount.toLocaleString() 
            : Number(amount).toLocaleString();
        
        return `${style.prefix}${currency} ${formattedAmount}`;
    }

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // =============================================
    // ANIMATIONS & UI EFFECTS
    // =============================================

    animateNewActivities() {
        const items = this.elements.list.querySelectorAll('.activity-item--animated');
        
        items.forEach((item, index) => {
            item.style.animationDelay = `${index * 0.05}s`;
            
            setTimeout(() => {
                item.classList.remove('activity-item--animated');
            }, 500 + (index * 50));
        });
    }

    // =============================================
    // STATE MANAGEMENT
    // =============================================

    setLoadingState(loading) {
        this.state.isLoading = loading;
        
        if (this.elements.loadingMsg) {
            this.elements.loadingMsg.style.display = loading ? 'block' : 'none';
        }
        
        if (loading) {
            this.elements.list.classList.add('loading');
        } else {
            this.elements.list.classList.remove('loading');
        }
    }

    updateEmptyState(isEmpty) {
        if (this.elements.emptyMsg) {
            this.elements.emptyMsg.style.display = isEmpty ? 'block' : 'none';
        }
        
        if (isEmpty) {
            this.elements.list.classList.add('empty');
        } else {
            this.elements.list.classList.remove('empty');
        }
    }

    // =============================================
    // EVENT HANDLERS
    // =============================================

    handleScroll() {
        if (!this.state.hasMore || this.state.isLoading) return;
        
        const scrollTop = window.scrollY || document.documentElement.scrollTop;
        const scrollHeight = document.documentElement.scrollHeight;
        const clientHeight = window.innerHeight;
        
        // Load more when 80% from bottom
        if (scrollTop + clientHeight >= scrollHeight * 0.8) {
            this.loadActivities(this.state.currentPage + 1, false);
        }
    }

    handleError(error) {
        console.error('Activity loading error:', error);
        
        // Show error state
        this.elements.list.innerHTML = `
            <li class="activity-error">
                <div class="activity-icon">
                    <i class="fas fa-exclamation-triangle text-danger"></i>
                </div>
                <div class="activity-details">
                    <div class="activity-title">Failed to load activities</div>
                    <div class="activity-time">Click to retry</div>
                </div>
                <div class="activity-amount">
                    <button onclick="window.activityManager.loadActivities()" class="btn-retry">
                        <i class="fas fa-redo"></i>
                    </button>
                </div>
            </li>
        `;
        
        this.elements.list.classList.add('error');
    }

    // =============================================
    // AUTO-REFRESH & UTILITIES
    // =============================================

    startAutoRefresh() {
        setInterval(() => {
            if (this.shouldRefresh() && !this.state.isLoading) {
                this.loadActivities(1, false);
            }
        }, this.config.refreshInterval);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    dispatchActivityUpdateEvent(count) {
        const event = new CustomEvent('activitiesUpdated', {
            detail: {
                count: count,
                timestamp: new Date(),
                activities: this.state.activities
            }
        });
        document.dispatchEvent(event);
        document.addEventListener('activitiesUpdated', (event) => {
    const activities = event.detail.activities || [];
    updateRecentActivitySummary({ activities }); 
});

    }

    // =============================================
    // PUBLIC METHODS
    // =============================================

    refresh() {
        this.loadActivities(1, false);
    }

    addActivity(activity) {
        this.state.activities.unshift(activity);
        
        if (this.state.activities.length > this.config.pageSize * 2) {
            this.state.activities = this.state.activities.slice(0, this.config.pageSize);
        }
        
        this.renderActivities();
    }

    getStats() {
        return {
            total: this.state.activities.length,
            lastUpdate: this.state.lastUpdate,
            types: this.state.activities.reduce((acc, activity) => {
                acc[activity.type] = (acc[activity.type] || 0) + 1;
                return acc;
            }, {})
        };
    }
}

class DailyBonusNotifier {
    constructor() {
        this.notificationContainer = null;
        this.init();
    }

    init() {
        // Create notification container
        this.createNotificationContainer();
        
        // Check for new bonuses on page load
        this.checkForNewBonuses();
        
        // Set up periodic checks (every 30 seconds)
        setInterval(() => this.checkForNewBonuses(), 30000);
    }

    createNotificationContainer() {
        this.notificationContainer = document.createElement('div');
        this.notificationContainer.id = 'bonus-notifications';
        this.notificationContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 350px;
        `;
        document.body.appendChild(this.notificationContainer);
    }

    async checkForNewBonuses() {
        try {
            const response = await fetch('/api/user/today-bonus');
            const data = await response.json();
            
            if (data.has_bonus && data.amount > 0) {
                this.showBonusNotification(data.amount, data.package_name);
                
                // Mark as seen to prevent duplicate notifications
                await this.markBonusAsSeen(data.bonus_id);
            }
        } catch (error) {
            console.log('Error checking bonuses:', error);
        }
    }

    showBonusNotification(amount, packageName = '') {
        // Check if notification already exists
        const existingNotification = document.querySelector('.bonus-notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        const notification = document.createElement('div');
        notification.className = 'bonus-notification';
        notification.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            margin-bottom: 10px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            animation: slideIn 0.5s ease-out;
            position: relative;
            min-width: 300px;
        `;

        const message = packageName 
            ? `Your daily bonus of $${amount} for ${packageName} has been paid! 🎉`
            : `Your daily bonus of $${amount} has been paid! 🎉`;

        notification.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <div style="font-weight: bold; font-size: 16px; margin-bottom: 5px;">Daily Bonus Paid!</div>
                    <div style="font-size: 14px; opacity: 0.9;">${message}</div>
                </div>
                <button class="close-bonus-notification" style="background: none; border: none; color: white; font-size: 18px; cursor: pointer; padding: 0; margin-left: 10px;">×</button>
            </div>
        `;

        // Add close button functionality
        notification.querySelector('.close-bonus-notification').addEventListener('click', () => {
            this.removeNotification(notification);
        });

        // Auto-remove after 8 seconds
        setTimeout(() => {
            this.removeNotification(notification);
        }, 8000);

        this.notificationContainer.appendChild(notification);

        // Add CSS animation
        this.addNotificationStyles();
    }

    removeNotification(notification) {
        notification.style.animation = 'slideOut 0.5s ease-in';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 500);
    }

    addNotificationStyles() {
        if (!document.getElementById('bonus-notification-styles')) {
            const styles = document.createElement('style');
            styles.id = 'bonus-notification-styles';
            styles.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes slideOut {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
                .bonus-notification:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.25);
                    transition: all 0.3s ease;
                }
            `;
            document.head.appendChild(styles);
        }
    }

    async markBonusAsSeen(bonusId) {
        try {
            await fetch('/api/user/mark-bonus-seen', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ bonus_id: bonusId })
            });
        } catch (error) {
            console.log('Error marking bonus as seen:', error);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new DailyBonusNotifier();
});

// Add this to your dashboard to show recent bonuses
class BonusDashboard {
    constructor() {
        this.container = document.getElementById('bonus-history');
        if (this.container) {
            this.loadBonusHistory();
        }
    }

    async loadBonusHistory() {
        try {
            const response = await fetch('/api/user/bonus-history');
            const bonuses = await response.json();
            
            this.renderBonusHistory(bonuses);
        } catch (error) {
            console.log('Error loading bonus history:', error);
        }
    }

    renderBonusHistory(bonuses) {
        if (!bonuses.length) {
            this.container.innerHTML = '<p>No bonus history available.</p>';
            return;
        }

        const html = `
            <div class="bonus-history-header">
                <h3>Recent Daily Bonuses</h3>
            </div>
            <div class="bonus-list">
                ${bonuses.map(bonus => `
                    <div class="bonus-item">
                        <div class="bonus-amount">+$${bonus.amount}</div>
                        <div class="bonus-details">
                            <div class="bonus-type">Daily Bonus</div>
                            <div class="bonus-date">${new Date(bonus.date).toLocaleDateString()}</div>
                        </div>
                        <div class="bonus-package">Package #${bonus.package_id}</div>
                    </div>
                `).join('')}
            </div>
        `;

        this.container.innerHTML = html;
    }
}

// Initialize RecentActivityManager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize EarningsDashboard (you already have this)
    window.earningsDashboard = new EarningsDashboard();
    
    // Initialize RecentActivityManager (MISSING - add this)
    window.activityManager = new RecentActivityManager();

        document.addEventListener('activitiesUpdated', (event) => {
        const activities = event.detail.activities || [];
        updateRecentActivitySummary({ activities });
    });
    
    console.log("✅ RecentActivityManager initialized");
});

//recent summary
function updateRecentActivitySummary(data) {
    const activities = data.activities || [];

    // Elements
    const weekCountEl = document.getElementById("activityWeekCount");
    const lastTitleEl = document.getElementById("lastActivityTitle");
    const lastAmountEl = document.getElementById("lastActivityAmount");
    const lastTimeEl = document.getElementById("lastActivityTime");

    // 1. Set weekly transaction count
    weekCountEl.textContent = activities.length;

    if (activities.length === 0) {
        lastTitleEl.textContent = "No activity yet";
        lastAmountEl.textContent = "—";
        lastTimeEl.textContent = "—";
        return;
    }

    // 2. Get MOST RECENT activity
    const latest = activities[0];

    // 3. Update summary fields
    lastTitleEl.textContent = latest.title;
    lastAmountEl.textContent = `${latest.amount.toLocaleString()} ${latest.currency}`;
    
    // Format time
    const ts = new Date(latest.timestamp);
    lastTimeEl.textContent = ts.toLocaleString();
}
