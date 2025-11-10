// Profile Page JavaScript
    // Application State
   

 
document.addEventListener("DOMContentLoaded", () => {
  // Fetch logged-in user data from API
  fetch("/user/profile")
    .then(res => {
      if (!res.ok) throw new Error("Unauthorized or error");
      return res.json();
    //  const userData = res
    })
    .then(user => {
      document.getElementById("memberSince").textContent = user.memberSince;
      document.getElementById("isVerified").textContent = user.isVerified;
      document.getElementById("isActive").textContent = user.isActive;
      document.getElementById("referralLink").textContent = user.referralLink;
      document.getElementById("username").textContent = user.username;
      document.getElementById("email").textContent = user.email;
      document.getElementById("phone").textContent = user.phone;
      document.getElementById("referral_code").textContent = user.referralCode;
      document.getElementById("balance").textContent = user.balance;
      document.getElementById("bonus").textContent = user.bonus;
      
    })
    .catch(err => {
      console.error("Error fetching profile:", err);
      document.getElementById("username").textContent = "Error loading profile";
    });
    });


    // Referral System
    const ReferralManager = {
        init() {
            if (!DOM.elements.copyLinkBtn) return;
            
            DOM.elements.copyLinkBtn.addEventListener('click', () => this.copyReferralLink());
        },
        
        async copyReferralLink() {
            if (!DOM.elements.referralLink) {
                UI.showError('Referral link not available');
                return;
            }
            
            const link = DOM.elements.referralLink.textContent;
            
            try {
                await navigator.clipboard.writeText(link);
                UI.showSuccess('Referral link copied to clipboard!');
            } catch (error) {
                console.error('Failed to copy referral link:', error);
                
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = link;
                document.body.appendChild(textArea);
                textArea.select();
                try {
                    document.execCommand('copy');
                    UI.showSuccess('Referral link copied to clipboard!');
                } catch (fallbackError) {
                    UI.showError('Failed to copy referral link');
                }
                document.body.removeChild(textArea);
            }
        }
    };

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
document.addEventListener('DOMContentLoaded', () => {
  const buttons = document.querySelectorAll('.pay-btn-modal');

  buttons.forEach(button => {
    button.addEventListener('click', async (event) => {
      // 1️⃣ Identify the modal (not the package card)
      const modal = event.target.closest('.payment-modal');

      // 2️⃣ Get amount and phone number from modal
      const amount = modal.getAttribute('data-amount');
      const phoneInput = modal.querySelector('.phone-input');
      const phone = phoneInput.value.trim();

      // 3️⃣ Validate phone
      const phoneRegex = /^(?:\+256|0)?7\d{8}$/;
      if (!phoneRegex.test(phone)) {
        alert("Please enter a valid phone number (Ugandan format)");
        return;
      }

      // 4️⃣ Prepare payload
      const payload = { amount: parseInt(amount), phone };

      try {
        // 5️⃣ Send to backend
        const response = await fetch('/payments/initiate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
          alert(data.error || "Payment initiation failed.");
          return;
        }

        // 6️⃣ Redirect or inform
        if (data.checkout_url) {
          window.location.href = data.checkout_url;
        } else {
          alert("Payment initiated. Please wait for confirmation.");
        }

      } catch (error) {
        console.error('Error:', error);
        alert("Network or server error. Try again later.");
      }
    });
  });
});


// Simply add this to your main JS file
document.addEventListener('DOMContentLoaded', function() {
    // Method 1: Simple initialization
    initProfileAvatar();
    
    // Method 2: For multiple avatars on page
    initSmartAvatar();
    
    // Method 3: Manual initialization for specific element
    const username = "aarons";
    const avatarElement = document.querySelector('.profile-avatar');
    avatarGenerator.updateExistingAvatar('.profile-avatar', username);
});