

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
// class EarningsDashboard {
//     constructor(options = {}) {
//         this.apiBaseUrl = options.apiBaseUrl || '';
//         this.refreshInterval = options.refreshInterval || 300000;
//         this.elements = {};
//         console.log("🎯 EarningsDashboard created");
//         this.init();
//     }

//     init() {
//         console.log("🔄 Initializing dashboard...");
//         this.cacheElements();
//         this.bindEvents();
//         this.loadEarnings();
        
//         if (this.refreshInterval > 0) {
//             setInterval(() => this.loadEarnings(), this.refreshInterval);
//         }
//     }

//     cacheElements() {
//         console.log("🔍 Caching HTML elements...");
        
//         // Main period elements
//         this.elements.today = document.getElementById('earningsToday');
//         this.elements.week = document.getElementById('earningsWeek');
//         this.elements.month = document.getElementById('earningsMonth');
        
//         // Breakdown elements
//         this.elements.referralBonus = document.getElementById('referral-bonus');
//         this.elements.signupBonus = document.getElementById('bonus');
//         this.elements.availableBalance = document.getElementById('available-balance');
//         this.elements.walletBalance = document.getElementById('wallet-balance');
//         this.elements.activeReferrals = document.getElementById('total-direct-referrals');
        
//         // Log what we found
//         console.log("📊 Elements found:", {
//             today: !!this.elements.today,
//             week: !!this.elements.week,
//             month: !!this.elements.month,
//             referralBonus: !!this.elements.referralBonus,
//             signupBonus: !!this.elements.signupBonus,
//             availableBalance: !!this.elements.availableBalance,
//             walletBalance: !!this.elements.walletBalance,
//             activeReferrals: !!this.elements.activeReferrals
//         });

//         // Create error container if needed
//         this.elements.errorContainer = document.getElementById('earnings-error') || this.createErrorContainer();
//     }

//     createErrorContainer() {
//         const container = document.createElement('div');
//         container.id = 'earnings-error';
//         container.className = 'alert alert-danger';
//         container.style.display = 'none';
        
//         // Try to find a container to put the error in
//         const mainContainer = document.querySelector('.container, main, body');
//         if (mainContainer) {
//             mainContainer.prepend(container);
//         }
        
//         return container;
//     }

//     bindEvents() {
//         const refreshBtn = document.getElementById('refresh-earnings');
//         if (refreshBtn) {
//             refreshBtn.addEventListener('click', () => this.loadEarnings());
//         }
//     }

//     async loadEarnings() {
//         console.log("📡 Fetching earnings data from API...");
        
//         try {
//             this.setLoadingState(true);
//             this.hideError();

//             const response = await fetch('/api/user/total-earnings', {
//                 method: 'GET',
//                 headers: {
//                     'Content-Type': 'application/json',
//                     'Accept': 'application/json'
//                 },
//                 credentials: 'same-origin'
//             });

//             console.log("📨 API Response status:", response.status);
            
//             if (!response.ok) {
//                 throw new Error(`HTTP error! status: ${response.status}`);
//             }

//             const data = await response.json();
//             console.log("✅ API Data received:", data);
            
//             if (data.error) {
//                 throw new Error(data.message || data.error);
//             }

//             this.updateDisplay(data);
//             this.setLoadingState(false);
//             console.log("🎉 Dashboard updated successfully!");

//         } catch (error) {
//             console.error('❌ Failed to load earnings:', error);
//             this.showError(error.message);
//             this.setLoadingState(false);
//         }
//     }

//     updateDisplay(data) {
//         console.log("🖥️ Updating display with data...");
        
//         // Update period totals
//         this.updateElement(this.elements.today, data.today);
//         this.updateElement(this.elements.week, data.this_week);
//         this.updateElement(this.elements.month, data.this_month);
        
//         // Update breakdown
//         if (data.breakdown) {
//             this.updateElement(this.elements.referralBonus, data.breakdown.referral_bonus);
//             this.updateElement(this.elements.signupBonus, data.breakdown.signup_bonus);
//             this.updateElement(this.elements.availableBalance, data.breakdown.available_balance);
//             this.updateElement(this.elements.walletBalance, data.breakdown.wallet_balance);
//             this.updateElement(this.elements.activeReferrals, data.referral_stats.total_direct_referrals);
//         }
//     }

//     updateElement(element, value) {
//         if (!element) {
//             console.log("⚠️ Element is null, cannot update");
//             return;
//         }
        
//         try {
//             const numericValue = parseFloat(value);
//             if (isNaN(numericValue)) {
//                 element.textContent = '0.00';
//                 return;
//             }
            
//             element.textContent = this.formatCurrency(numericValue);
//             console.log(`✅ Updated ${element.id} to: ${element.textContent}`);
//         } catch (error) {
//             console.error('Error updating element:', error);
//             element.textContent = '0.00';
//         }
//     }

//     formatCurrency(amount) {
//         return new Intl.NumberFormat('en-US', {
//             minimumFractionDigits: 2,
//             maximumFractionDigits: 2
//         }).format(amount);
//     }

//     setLoadingState(loading) {
//         // Simple loading state - you can enhance this later
//         Object.values(this.elements).forEach(element => {
//             if (element && element.style) {
//                 element.style.opacity = loading ? '0.6' : '1';
//             }
//         });
//     }

//     showError(message) {
//         console.error("💥 Showing error:", message);
//         if (this.elements.errorContainer) {
//             this.elements.errorContainer.textContent = `Error: ${message}`;
//             this.elements.errorContainer.style.display = 'block';
//         }
//     }

//     hideError() {
//         if (this.elements.errorContainer) {
//             this.elements.errorContainer.style.display = 'none';
//         }
//     }

//     refresh() {
//         this.loadEarnings();
//     }
// }
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
        this.elements.total = document.getElementById('earningsTotal'); // Add this to HTML
        
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
            total: !!this.elements.total,
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
        
        // Update period totals (these are at root level)
        this.updateElement(this.elements.today, data.today);
        this.updateElement(this.elements.week, data.this_week);
        this.updateElement(this.elements.month, data.this_month);
        
        // Update lifetime total from lifetime_earnings.total
        if (data.lifetime_earnings && data.lifetime_earnings.total) {
            this.updateElement(this.elements.total, data.lifetime_earnings.total);
        }
        
        // Update breakdown - FIXED: Use data.breakdown (not data.breakdown inside breakdown)
        if (data.breakdown) {
            console.log("💰 Updating breakdown values:", data.breakdown);
            
            // Referral bonus from current breakdown
            this.updateElement(this.elements.referralBonus, data.breakdown.referral_bonus);
            
            // Signup bonus from current breakdown
            this.updateElement(this.elements.signupBonus, data.breakdown.signup_bonus);
            
            // Available balance from current breakdown
            this.updateElement(this.elements.availableBalance, data.breakdown.available_balance);
            
            // Wallet balance from current breakdown
            this.updateElement(this.elements.walletBalance, data.breakdown.wallet_balance);
        }
        
        // Update referral stats
        if (data.referral_stats) {
            console.log("👥 Updating referral stats:", data.referral_stats);
            
            // Use total_direct_referrals from referral_stats
            this.updateElement(this.elements.activeReferrals, data.referral_stats.total_direct_referrals);
        }
        
        // If you want to display lifetime referral bonus separately:
        if (data.lifetime_earnings && data.lifetime_earnings.breakdown) {
            console.log("📈 Lifetime referral bonus:", data.lifetime_earnings.breakdown.referral_bonus);
            // You could update a separate element here if needed
        }
    }

    updateElement(element, value) {
        if (element) {
            // Format as currency with 2 decimal places if it's a number
            let displayValue = value;
            if (value !== undefined && value !== null && !isNaN(parseFloat(value))) {
                const numValue = parseFloat(value);
                displayValue = numValue.toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            } else if (value === undefined || value === null) {
                displayValue = '0.00';
            }
            
            element.textContent = displayValue;
            console.log(`✅ Updated ${element.id} to:`, displayValue);
        } else {
            console.warn("⚠️ Element not found for update");
        }
    }

    setLoadingState(isLoading) {
        // Add loading indicators if needed
        const loader = document.getElementById('earnings-loader');
        if (loader) {
            loader.style.display = isLoading ? 'block' : 'none';
        }
    }

    showError(message) {
        if (this.elements.errorContainer) {
            this.elements.errorContainer.textContent = message;
            this.elements.errorContainer.style.display = 'block';
        }
    }

    hideError() {
        if (this.elements.errorContainer) {
            this.elements.errorContainer.style.display = 'none';
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.earningsDashboard = new EarningsDashboard();
});

// // Initialize when DOM is ready
// console.log("🚀 Earnings dashboard script loaded, waiting for DOM...");

// if (document.readyState === 'loading') {
//     document.addEventListener('DOMContentLoaded', () => {
//         console.log("📄 DOM Content Loaded - Initializing EarningsDashboard");
//         window.earningsDashboard = new EarningsDashboard();
//     });
// } else {
//     console.log("⚡ DOM already ready - Initializing EarningsDashboard immediately");
//     window.earningsDashboard = new EarningsDashboard();
// }


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
    constructor(userId) {
        this.userId = userId;
        this.config = {
            apiEndpoint: `/api/recent_activity/user`,                                          //'/api/recent_activity',
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
            const url =  `${this.config.apiEndpoint}?page=${page}&page_size=${this.config.pageSize}`;                                                 //`${this.config.apiEndpoint}?page=${page}&page_size=${this.config.pageSize}`;
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


// async function initRecentActivity() {
//     const resp = await fetch("/api/whoami");
//     const data = await resp.json();
//     const recentActivity = new RecentActivityFetcher(data.user_id);
//     recentActivity.startAutoRefresh();
//     console.log(data);
//}
async function init() {
    const resp = await fetch("/api/whoami");
    const data = await resp.json();
    console.log(data);
}

init();


// /*VERIFY OTP */
// const verifyBtn = document.getElementById('verifyOtpBtn');
// if (verifyBtn) {
//     verifyBtn.addEventListener('click', async () => {
//         const otp = document.getElementById('otpInput').value;

//         if (!otp) {
//             showAlert("Enter OTP", true);
//             return;
//         }

//         verifyBtn.disabled = true;
//         verifyBtn.innerHTML = 'Verifying...';

//         try {
//             await apiCall('/api/verify-otp', {
//                 method: 'POST',
//                 body: JSON.stringify({ otp })
//             });

//             showAlert("Verification successful!");
//             loadVerificationStatus(); // refresh UI

//         } catch (err) {
//             showAlert(`Verification failed: ${err.message}`, true);
//             verifyBtn.disabled = false;
//             verifyBtn.innerHTML = 'Verify';
//         }
//     });
// }
// /* RESEND VERIFICATION OTP */
// const resendBtn = document.getElementById('resendOtpBtn');
// if (resendBtn) {
//     resendBtn.addEventListener('click', async () => {
//         resendBtn.disabled = true;
//         resendBtn.innerHTML = 'Sending...';

//         try {
//             await apiCall('/api/request-verification', { method: 'POST' });
//             showAlert("OTP resent!");
//         } catch (err) {
//             showAlert(`Resend failed: ${err.message}`, true);
//         }

//         resendBtn.disabled = false;
//         resendBtn.innerHTML = 'Resend';
//     });
// }

// function attachOTPEvents() {
//     const verifyBtn = document.getElementById('verifyOtpBtn');
//     const resendBtn = document.getElementById('resendOtpBtn');

//     if (verifyBtn) {
//         verifyBtn.addEventListener('click', async () => {
//             const otp = document.getElementById('otpInput').value;

//             if (!otp) {
//                 showAlert("Enter OTP", true);
//                 return;
//             }

//             verifyBtn.disabled = true;
//             verifyBtn.innerHTML = 'Verifying...';

//             try {
//                 await apiCall('/api/verify-otp', {
//                     method: 'POST',
//                     body: JSON.stringify({ otp })
//                 });

//                 showAlert("Verification successful!");
//                 loadVerificationStatus(); // refresh final state

//             } catch (err) {
//                 showAlert(`Verification failed: ${err.message}`, true);
//                 verifyBtn.disabled = false;
//                 verifyBtn.innerHTML = 'Verify';
//             }
//         });
//     }

//     if (resendBtn) {
//         resendBtn.addEventListener('click', async () => {
//             resendBtn.disabled = true;
//             resendBtn.innerHTML = 'Sending...';

//             try {
//                 await apiCall('/api/request-verification', { method: 'POST' });
//                 showAlert("OTP resent!");
//             } catch (err) {
//                 showAlert(`Resend failed: ${err.message}`, true);
//             }

//             resendBtn.disabled = false;
//             resendBtn.innerHTML = 'Resend';
//         });
//     }
// }
// ``



// network-dashboard.js

/**
 * Network Dashboard Module
 * Handles fetching and displaying user network data
 */

class NetworkDashboard {
    constructor(userId) {
        this.userId = userId;
        this.apiEndpoint = `/api/user/${userId}/network`;
        this.elements = {
            networkSize: null,
            networkDepth: null,
            directReferrals: null
        };
    }

    /**
     * Initialize the dashboard
     */
    async init() {
        this.captureElements();
        await this.loadAndDisplayNetworkData();
    }

    /**
     * Capture DOM elements with error handling
     */
    captureElements() {
        this.elements.networkSize = document.getElementById('network-size');
        this.elements.networkDepth = document.getElementById('network-depth');
        
        // Create direct referrals element if it doesn't exist
        if (!document.getElementById('direct-referrals')) {
            this.createDirectReferralsElement();
        }
        this.elements.directReferrals = document.getElementById('direct-referrals');
    }

    /**
     * Create the direct referrals element if missing
     */
    createDirectReferralsElement() {
        const networkCard = document.getElementById('statNetworkGrowth');
        if (networkCard) {
            const directReferralsDiv = document.createElement('div');
            directReferralsDiv.id = 'direct-referrals';
            directReferralsDiv.className = 'direct-referrals-stats';
            directReferralsDiv.style.marginTop = '15px';
            directReferralsDiv.style.padding = '10px';
            directReferralsDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.02)';
            directReferralsDiv.style.borderRadius = '8px';
            
            // Insert after the network-depth element
            const depthElement = document.getElementById('network-depth');
            if (depthElement && depthElement.parentNode) {
                depthElement.parentNode.insertBefore(directReferralsDiv, depthElement.nextSibling);
            } else {
                networkCard.appendChild(directReferralsDiv);
            }
        }
    }

    /**
     * Fetch network data from API
     */
    async fetchNetworkData() {
        try {
            const response = await fetch(this.apiEndpoint);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to fetch network data');
            }
            
            return data.network;
            
        } catch (error) {
            console.error('API fetch error:', error);
            throw error;
        }
    }

    /**
     * Format numbers with commas (e.g., 1200 -> 1,200)
     */
    formatNumber(num) {
        if (num === undefined || num === null) return '0';
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    /**
     * Get motivational message based on network size
     */
    getMotivationalMessage(networkSize, directDescendants, depth) {
        if (networkSize === 0) {
            return "Start building your network today! Every referral counts.";
        } else if (networkSize < 10) {
            return "Great start! Keep growing your network.";
        } else if (networkSize < 50) {
            return "Impressive growth! You're building a strong community.";
        } else if (networkSize < 100) {
            return "Outstanding! Your network is thriving.";
        } else {
            return "Exceptional! You're a true network leader! 🎉";
        }
    }

    /**
     * Update the UI with network data
     */
    renderNetworkCard(networkData) {
        const {
            direct_descendants_count = 0,
            total_network_size = 0,
            network_depth = 0
        } = networkData;

        // Format numbers
        const formattedNetworkSize = this.formatNumber(total_network_size);
        const formattedDirectReferrals = this.formatNumber(direct_descendants_count);
        
        // Get card container
        const networkCard = document.getElementById('statNetworkGrowth');
        
        // Update network size
        if (this.elements.networkSize) {
            this.elements.networkSize.innerHTML = `
                <div style="margin: 10px 0 5px 0; font-size: 14px; color: #666;">
                    <i class="fas fa-chart-network"></i> Total Network Size
                </div>
                <div style="font-size: 32px; font-weight: bold; color: #2c3e50;">
                    ${formattedNetworkSize}
                </div>
                <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">
                    ${this.getMotivationalMessage(total_network_size, direct_descendants_count, network_depth)}
                </div>
            `;
        }
        
        // Update network depth
        if (this.elements.networkDepth) {
            this.elements.networkDepth.innerHTML = `
                <div style="margin: 10px 0 5px 0; font-size: 14px; color: #666;">
                    <i class="fas fa-layer-group"></i> Network Depth
                </div>
                <div style="font-size: 24px; font-weight: bold; color: #3498db;">
                    ${network_depth} Levels
                </div>
                <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">
                    Your influence reaches ${network_depth} levels deep
                </div>
            `;
        }
        
        // Update direct referrals
        if (this.elements.directReferrals) {
            this.elements.directReferrals.innerHTML = `
                <div style="margin: 5px 0 5px 0; font-size: 14px; color: #666;">
                    <i class="fas fa-user-friends"></i> Direct Referrals
                </div>
                <div style="font-size: 24px; font-weight: bold; color: #2ecc71;">
                    ${formattedDirectReferrals} People
                </div>
                <div style="font-size: 12px; color: #7f8f8d; margin-top: 5px;">
                    You directly referred ${formattedDirectReferrals} ${direct_descendants_count === 1 ? 'person' : 'people'}
                </div>
            `;
        }
        
        // Update the main stat value (growth indicator)
        const statValueElement = networkCard?.querySelector('.main-stat-value');
        if (statValueElement && total_network_size > 0) {
            // You can calculate growth based on previous data if available
            // For now, showing a friendly message
            statValueElement.innerHTML = `🎯 ${formattedNetworkSize}`;
        }
        
        const statLabelElement = networkCard?.querySelector('.main-stat-label');
        if (statLabelElement) {
            statLabelElement.innerHTML = `Total Network Members`;
        }
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        const loadingMessage = `
            <div style="text-align: center; padding: 20px;">
                <i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #3498db;"></i>
                <p style="margin-top: 10px; color: #666;">Loading network data...</p>
            </div>
        `;
        
        if (this.elements.networkSize) {
            this.elements.networkSize.innerHTML = loadingMessage;
        }
        if (this.elements.networkDepth) {
            this.elements.networkDepth.innerHTML = loadingMessage;
        }
        if (this.elements.directReferrals) {
            this.elements.directReferrals.innerHTML = loadingMessage;
        }
    }

    /**
     * Show error state
     */
    showErrorState(errorMessage) {
        const errorHtml = `
            <div style="text-align: center; padding: 15px; background: #fee; border-radius: 8px; color: #c0392b;">
                <i class="fas fa-exclamation-triangle" style="font-size: 20px;"></i>
                <p style="margin-top: 8px; font-size: 13px;">${errorMessage}</p>
                <button onclick="location.reload()" style="margin-top: 10px; padding: 5px 12px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    Retry
                </button>
            </div>
        `;
        
        if (this.elements.networkSize) {
            this.elements.networkSize.innerHTML = errorHtml;
        }
        
        console.error('Network Dashboard Error:', errorMessage);
    }

    /**
     * Main function to load and display data
     */
    async loadAndDisplayNetworkData() {
        try {
            // Show loading state
            this.showLoadingState();
            
            // Fetch data from API
            const networkData = await this.fetchNetworkData();
            
            // Update UI with fetched data
            this.renderNetworkCard(networkData);
            
        } catch (error) {
            // Handle errors gracefully
            let userFriendlyMessage = 'Unable to load network data. Please try again later.';
            
            if (error.message.includes('404')) {
                userFriendlyMessage = 'Network data not found.';
            } else if (error.message.includes('500')) {
                userFriendlyMessage = 'Server error. Please try again later.';
            } else if (error.message.includes('Failed to fetch')) {
                userFriendlyMessage = 'Network connection error. Please check your internet.';
            }
            
            this.showErrorState(userFriendlyMessage);
        }
    }
}

/**
 * Helper function to get current user ID
 * Modify this based on how your app stores user data
 */
function getCurrentUserId() {
    // Option 1: From global variable
    if (window.currentUserId) {
        return window.currentUserId;
    }
    
    // Option 2: From localStorage
    const storedUserId = localStorage.getItem('userId');
    if (storedUserId) {
        return parseInt(storedUserId);
    }
    
    // Option 3: From meta tag
    const metaTag = document.querySelector('meta[name="user-id"]');
    if (metaTag) {
        return parseInt(metaTag.getAttribute('content'));
    }
    
    // Option 4: Default demo user (replace with actual logic)
    console.warn('No user ID found, using default (1)');
    return 1; // Demo user ID
}

/**
 * Initialize the dashboard when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    const userId = getCurrentUserId();
    const dashboard = new NetworkDashboard(userId);
    dashboard.init();
});

// Export for module usage (if using modules)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { NetworkDashboard };
}

// notifications.js - SINGLE CLEAN VERSION

// Helper function - define once
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Single loadNotifications function
async function loadNotifications() {
    // Use the correct container from your HTML
    const container = document.getElementById('notificationsContent');
    const countElement = document.getElementById('notificationsCount');
    
    // Safety check - exit if elements don't exist
    if (!container) {
        console.warn('notificationsContent element not found in DOM');
        return;
    }
    
    try {
        const response = await fetch('/api/notifications', {
            headers: {
                'Content-Type': 'application/json'
                // Remove Authorization if using session auth
                // 'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to load notifications');
        
        const notifications = await response.json();
        
        // Update count if element exists
        if (countElement) {
            const unreadCount = notifications.filter(n => !n.is_read).length;
            countElement.textContent = unreadCount;
        }
        
        if (!notifications || notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-bell-slash text-muted mb-2" style="font-size: 24px;"></i>
                    <p class="text-muted mb-0">No notifications yet</p>
                </div>
            `;
            return;
        }
        
        // Show only last 5 notifications
        const recent = notifications.slice(0, 5);
        
        let html = '<div class="notifications-list">';
        for (let notif of recent) {
            const date = notif.created_at ? new Date(notif.created_at).toLocaleDateString() : 'Recent';
            html += `
                <div class="notification-item ${notif.is_read ? 'read' : ''}" data-id="${notif.id}">
                    <div class="notification-icon">
                        <i class="fas ${notif.is_read ? 'fa-envelope-open' : 'fa-envelope'}"></i>
                    </div>
                    <div class="notification-content">
                        <div class="notification-message">${escapeHtml(notif.message)}</div>
                        <div class="notification-date">${date}</div>
                    </div>
                    ${!notif.is_read ? '<div class="notification-unread-dot"></div>' : ''}
                </div>
            `;
        }
        html += '</div>';
        
        container.innerHTML = html;
        
        // Add click handlers to mark as read
        document.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', async () => {
                const id = item.dataset.id;
                if (!item.classList.contains('read')) {
                    try {
                        await fetch(`/api/notifications/${id}/read`, { method: 'PUT' });
                        item.classList.add('read');
                        const dot = item.querySelector('.notification-unread-dot');
                        if (dot) dot.remove();
                        
                        // Update unread count
                        if (countElement) {
                            const currentCount = parseInt(countElement.textContent) || 0;
                            countElement.textContent = Math.max(0, currentCount - 1);
                        }
                    } catch (err) {
                        console.error('Failed to mark as read:', err);
                    }
                }
            });
        });
        
    } catch (err) {
        console.error('Error loading notifications:', err);
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-exclamation-triangle text-warning mb-2" style="font-size: 24px;"></i>
                <p class="text-muted mb-0">Failed to load notifications</p>
                <button onclick="loadNotifications()" class="btn btn-sm btn-outline-primary mt-2">
                    <i class="fas fa-sync-alt"></i> Retry
                </button>
            </div>
        `;
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (document.getElementById('notificationsContent')) {
            loadNotifications();
            // Refresh every 30 seconds
            setInterval(loadNotifications, 30000);
        }
    });
} else {
    if (document.getElementById('notificationsContent')) {
        loadNotifications();
        setInterval(loadNotifications, 30000);
    }
}
// Update function mapping
function updateDashboardUI(data) {
    // Wallet balances
    document.getElementById('wallet-balance').textContent = formatNumber(data.wallet_balance || 0);
    document.getElementById('available-balance-subnote').textContent = formatNumber(data.available_balance || 0);
    document.getElementById('available-balance-mini').textContent = formatNumber(data.available_balance || 0);
    
    // Mini stats
    document.getElementById('actual-balance').textContent = formatNumber(data.actual_balance || 0);
    document.getElementById('referral-bonus-mini').textContent = formatNumber(data.referral_bonus || 0);
    document.getElementById('bonus-mini').textContent = formatNumber(data.bonus || 0);
    document.getElementById('earnings-total-mini').textContent = formatNumber(data.lifetime_earnings?.total || 0);
    
    // Financial summary
    document.getElementById('earnings-today').textContent = formatNumber(data.today || 0);
    document.getElementById('earnings-week').textContent = formatNumber(data.this_week || 0);
    document.getElementById('earnings-total').textContent = formatNumber(data.lifetime_earnings?.total || 0);
    
    // Main section
    document.getElementById('main-direct-referrals').textContent = data.referral_stats?.direct_referrals_count || 0;
    document.getElementById('main-referral-bonus').textContent = formatNumber(data.referral_bonus || 0);
    
    // Profile
    document.getElementById('profile-email').textContent = data.email || 'Not set';
    document.getElementById('profile-phone').textContent = data.phone || 'Not set';
    document.getElementById('profile-verified').textContent = data.is_verified ? 'Yes' : 'No';
    document.getElementById('profile-join-date').textContent = formatDate(data.memberSince);
    
    // Direct referrals
    const referralCount = data.referral_stats?.direct_referrals_count || 0;
    document.getElementById('total-direct-referrals-mini').textContent = referralCount;
    document.getElementById('main-direct-referrals').textContent = referralCount;
}

