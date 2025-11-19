// Profile Page JavaScript
    // Application State
   

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
      document.getElementById("referralLink").textContent = user.referralLink || 'N/A';
      document.getElementById("username").textContent = user.username || 'N/A';
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
            
            // User avatar (logout)
            if (DOM.elements.userAvatar) {
                DOM.elements.userAvatar.addEventListener('click', () => {
                    this.confirmLogout();
                });
            }
        },
        
        showNotifications() {
            UI.showMessage('Notifications feature coming soon!', 'info');
        },
        
        showSettings() {
            UI.showMessage('Settings feature coming soon!', 'info');
        },
        
        async confirmLogout() {
            const confirmed = confirm('Are you sure you want to logout?');
            if (!confirmed) return;
            
            try {
                await API.logout();
                window.location.href = '/index'; 
            } catch (error) {
                console.error('Logout failed:', error);
                UI.showError('Logout failed. Please try again.');
            }
        }
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