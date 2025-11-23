

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
      document.getElementById("isActive").textContent = user.isActive ? 'Active' : 'Inactive';
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
        
        // Log what we found
        console.log("📊 Elements found:", {
            today: !!this.elements.today,
            week: !!this.elements.week,
            month: !!this.elements.month,
            referralBonus: !!this.elements.referralBonus,
            signupBonus: !!this.elements.signupBonus,
            availableBalance: !!this.elements.availableBalance,
            walletBalance: !!this.elements.walletBalance
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
