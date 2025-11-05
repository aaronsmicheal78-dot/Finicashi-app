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

// const ModalManager = {
//     init: function() {
//         this.setupEventListeners();
//         this.setupOpenButtons();
//     },

//     setupEventListeners: function() {
//         // Close buttons
//         document.querySelectorAll('.close-modal, .close-form').forEach(button => {
//             button.addEventListener('click', (e) => {
//                 e.preventDefault();
//                 this.closeAllModals();
//             });
//         });

//         // Clicking outside modal content
//         document.querySelectorAll('.modal').forEach(modal => {
//             modal.addEventListener('click', (e) => {
//                 if (e.target === modal) {
//                     this.closeAllModals();
//                 }
//             });
//         });

//         // Escape key
//         document.addEventListener('keydown', (e) => {
//             if (e.key === 'Escape') {
//                 this.closeAllModals();
//             }
//         });
//     },

//     setupOpenButtons: function() {
//         // Automatically bind all buttons with data-modal
//         document.querySelectorAll('[data-modal]').forEach(button => {
//             button.addEventListener('click', () => {
//                 const modalId = button.dataset.modal;
//                 this.openModal(modalId);
//             });
//         });
//     },

//     openModal: function(modalId) {
//         const modal = document.getElementById(modalId);
//         if (!modal) return;

//         this.closeAllModals();
//         modal.style.display = 'flex';
//         modal.style.visibility = 'visible';
//         modal.style.opacity = '1';
//         modal.classList.add('active');
//     },

//     closeAllModals: function() {
//         document.querySelectorAll('.modal').forEach(modal => {
//             modal.style.display = 'none';
//             modal.style.visibility = 'hidden';
//             modal.style.opacity = '0';
//             modal.classList.remove('active');
//         });
//     }
// };

// // Initialize after DOM loaded
// document.addEventListener('DOMContentLoaded', () => {
//     ModalManager.init();
// });
