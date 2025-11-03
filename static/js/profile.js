   // DOM Elements
    //     const profileData = {
    //         username: "johnd",
    //         name: "John Davidson",
    //         email: "john.davidson@example.com",
    //         phone: "+1 (555) 123-4567",
    //         balance: 42580.00,
    //         referralCode: "FINPRO24",
    //         referralLink: "https://fincash.pro/ref/FINPRO24",
    //         joined: "Jan 15, 2022",
    //         verified: true,
    //         active: true,
    //         totalReferrals: 24,
    //         avatarInitials: "JD"
    //     };

    //     // Populate profile data
    //     document.addEventListener('DOMContentLoaded', function() {
    //         // Profile data
            
    //         const userData = res
    // })
    //         .then(user => {
    //         document.getElementById("memberSince").textContent = user.memberSince;
    //   document.getElementById("isVerified").textContent = user.isVerified;
    //   document.getElementById("isActive").textContent = user.isActive;
    //   document.getElementById("referralLink").textContent = user.referrallink;
    //   document.getElementById("username").textContent = user.username;
    //   document.getElementById("email").textContent = user.email;
    //   document.getElementById("phone").textContent = user.phone;
    //   document.getElementById("referral_code").textContent = user.referral_code;
    //   document.getElementById("balance").textContent = user.balance;
    //   document.getElementById("bonus").textContent = user.bonus;
    //         // Status badges
    //         if (!profileData.verified) {
    //             document.getElementById('verified').textContent = "Not Verified";
    //             document.getElementById('verified').classList.remove('status-verified');
    //             document.getElementById('verified').classList.add('status-inactive');
    //         }
            
    //         if (!profileData.active) {
    //             document.getElementById('active').textContent = "Inactive";
    //             document.getElementById('active').classList.remove('status-active');
    //             document.getElementById('active').classList.add('status-inactive');
    //         }

            // Copy referral link functionality
            document.getElementById('copy-link').addEventListener('click', function() {
                const referralLink = document.getElementById('referral-link').textContent;
                navigator.clipboard.writeText(referralLink).then(() => {
                    const originalText = this.textContent;
                    this.textContent = 'Copied!';
                    setTimeout(() => {
                        this.textContent = originalText;
                    }, 2000);
                });
            });

            // Modal functionality
            const packageCards = document.querySelectorAll('.package-card');
            const modals = document.querySelectorAll('.modal');
            const closeButtons = document.querySelectorAll('.close-modal, .close-form');

            packageCards.forEach(card => {
                card.addEventListener('click', function() {
                    const modalId = this.getAttribute('data-modal');
                    document.getElementById(modalId).style.display = 'flex';
                });
            });

            closeButtons.forEach(button => {
                button.addEventListener('click', function() {
                    this.closest('.modal').style.display = 'none';
                });
            });

            // Close modal when clicking outside content
            modals.forEach(modal => {
                modal.addEventListener('click', function(e) {
                    if (e.target === this) {
                        this.style.display = 'none';
                    }
                });
            });

            // Invest Now buttons
            const investButtons = document.querySelectorAll('[id^="pay-"]');
            investButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const modalId = this.closest('.modal').id;
                    const amountInput = document.querySelector(`#${modalId} input[type="number"]`);
                    const phoneInput = document.querySelector(`#${modalId} input[type="tel"]`);
                    
                    if (!amountInput.value || !phoneInput.value) {
                        alert('Please fill in all required fields');
                        return;
                    }
                    
                    const amount = parseFloat(amountInput.value);
                    const min = parseFloat(amountInput.min);
                    const max = parseFloat(amountInput.max);
                    
                    if (amount < min || (max && amount > max)) {
                        if (max) {
                            alert(`Please enter an amount between $${min} and $${max}`);
                        } else {
                            alert(`Please enter an amount of at least $${min}`);
                        }
                        return;
                    }
                    
                    // In a real app, this would process the payment
                    alert(`Investment of $${amount} submitted successfully!`);
                    this.closest('.modal').style.display = 'none';
                    
                    // Reset form
                    amountInput.value = '';
                    phoneInput.value = '';
                    if (document.querySelector(`#${modalId} textarea`)) {
                        document.querySelector(`#${modalId} textarea`).value = '';
                    }
                }); });
        
        

           
        document.addEventListener('DOMContentLoaded', () => {
    const logoutBtn = document.getElementById('logout-btn');

    if (logoutBtn) {
        logoutBtn.addEventListener('click', logoutUser);
    }
});

async function logoutUser() {
    try {
        // Optional: show confirmation
        const confirmed = confirm("Are you sure you want to log out?");
        if (!confirmed) return;

        // Call the Flask logout route
        const response = await fetch('/api/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            // Clear client storage
            sessionStorage.clear();
            localStorage.removeItem('auth_token');

            // Optional: small fade-out transition before redirect
            document.body.style.opacity = '0';
            setTimeout(() => {
                window.location.href = '/'; 
            }, 300);
        } else {
            alert('Logout failed: ' + data.message);
        }
    } catch (error) {
        console.error('Logout error:', error);
        alert('An error occurred while logging out.');
    }
}

document.querySelectorAll('.investment-form .invest-now-btn').forEach(button => {
  button.addEventListener('click', async (event) => {
    // Find the form that contains this button
    const form = button.closest('.investment-form');
    const amount = parseInt(form.getAttribute('data-amount'), 10);
    const phoneInput = form.querySelector('input[name="phone"]');
    const phone = phoneInput ? phoneInput.value.trim() : '';

    // Basic validation
    if (!phone) {
      alert('Please enter your phone number.');
      return;
    }

    // Optional: validate phone format (e.g., Ugandan number)
    const phoneRegex = /^(?:\+256|0)?[7][0-9]{8}$/;
    if (!phoneRegex.test(phone)) {
      alert('Please enter a valid Ugandan phone number (e.g., 07XXXXXXXX or +2567XXXXXXXX).');
      return;
    }

    // Send to Flask
    try {
      const response = await fetch('/payment/initiate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ amount, phone })
      });

      const result = await response.json();

      if (response.ok) {
        // Success: maybe redirect or show success message
        alert('Payment initiated! Check your phone for confirmation.');
        console.log('Success:', result);
      } else {
        alert('Payment failed: ' + (result.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Network error:', error);
      alert('Failed to connect. Please try again.');
    }
  });
});
   