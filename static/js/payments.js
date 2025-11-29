document.addEventListener("click", async (event) => {
  const payButton = event.target.closest(".pay-btn");
  if (!payButton) return;

  // Prevent multiple clicks
  if (payButton.disabled) return;

  const modal = payButton.closest(".payment-modal");
  if (!modal) return;

  // Get modal type and inputs
  const packageType = modal.getAttribute("data-package");
  const phoneInput = modal.querySelector(".phone-input");
  
  if (!phoneInput) {
    alert("Missing phone input field.");
    return;
  }

  const phone = phoneInput.value.trim();
  
  if (!phone) {
    alert("Please enter your phone number.");
    return;
  }

  let amount;
  
  // Determine amount based on package type
  if (packageType === "deposit") {
    // For deposits, get amount from input field
    const amountInput = modal.querySelector(".amount-input");
    if (!amountInput) {
      alert("Missing amount input for deposit.");
      return;
    }
    amount = amountInput.value.trim();
  } else {
    // For packages, get amount from data attribute
    amount = modal.getAttribute("data-amount");
  }

  // Validate amount
  if (!amount) {
    alert("Amount is required.");
    return;
  }

  const amountNum = parseFloat(amount);
  if (isNaN(amountNum) || amountNum <= 0) {
    alert("Please enter a valid amount.");
    return;
  }

  // Determine transaction type
  const transactionType = packageType === "deposit" ? "deposit" : "package";

  // Create payment data with required fields
  const paymentData = {
    amount: amountNum,
    phone: phone,
    payment_type: transactionType  // This tells Flask whether it's deposit or package
  };

  // Add package name to payload for package purchases
  if (transactionType === "package") {
    paymentData.package = packageType; // Add package name (bronze, silver, gold, etc.)
  }

  console.log("Sending payment data:", paymentData);

  // Disable button and show loading state
  const originalText = payButton.textContent;
  payButton.disabled = true;
  payButton.textContent = "Processing...";

  try {
    const response = await fetch('/payments/initiate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(paymentData)
    });

    const result = await response.json();
    
    if (response.ok) {
      alert('Payment initiated successfully!');
      // Close modal
      modal.style.display = 'none';
      // Optionally reset form
      if (packageType === "deposit") {
        modal.querySelector(".amount-input").value = '';
      }
      modal.querySelector(".phone-input").value = '';
    } else {
      alert('Error: ' + (result.error || 'Unknown error occurred'));
    }
  } catch (error) {
    console.error('Error:', error);
    alert('Network error occurred. Please try again.');
  } finally {
    // Re-enable button regardless of outcome
    payButton.disabled = false;
    payButton.textContent = originalText;
  }
});

// Fetch current user with all relationships
async function fetchCurrentUser() {
    try {
        const response = await fetch('/user/profile');
        if (!response.ok) throw new Error('Failed to fetch user');
        return await response.json();
    } catch (error) {
        console.error('Error fetching user:', error);
        return null;
    }
}

// Format currency helper
function formatCurrency(amount) {
    if (amount === undefined || amount === null) return '0';
    return new Intl.NumberFormat('en-UG').format(amount);
}

// Update dashboard with user data
function updateDashboard(userData) {
    console.log("Updating dashboard with:", userData);
    
    // Update balance displays if elements exist
    const availableBalanceElement = document.getElementById("available-balance");
    const actualBalanceElement = document.getElementById("actual-balance");
    const bonusElement = document.getElementById("bonus");
    const referralBonusElement = document.getElementById("referral-bonus");
    
    if (availableBalanceElement) {
        // Try different possible field names
        const availableBalance = userData.availableBalance || userData.balance || 0;
        availableBalanceElement.textContent = formatCurrency(availableBalance);
    }
    
    if (actualBalanceElement) {
        // Try different possible field names
        const actualBalance = userData.actualBalance || userData.balance || 0;
        actualBalanceElement.textContent = formatCurrency(actualBalance);
    }
    
    if (bonusElement) {
        bonusElement.textContent = formatCurrency(userData.bonus || 0);
    }
    
    if (referralBonusElement) {
        // If you have a separate referral bonus field
        const referralBonus = userData.referralBonus || userData.bonus || 0;
        referralBonusElement.textContent = formatCurrency(referralBonus);
    }
}

// Display user packages
function displayPackages(packages) {
    const packageElement = document.getElementById("package");
    if (!packageElement) return;
    
    if (packages && packages.length > 0) {
        const packageNames = packages.map(pkg => pkg.name).join(', ');
        packageElement.textContent = packageNames;
    } else {
        packageElement.textContent = "No active package";
    }
}

// Update bonus display
function updateBonusDisplay(bonus) {
    const bonusElement = document.getElementById("bonus");
    if (bonusElement) {
        bonusElement.textContent = formatCurrency(bonus || 0);
    }
}

// Usage in updating user profile with bonus, user data, package
async function loadUserProfile() {
    const userData = await fetchCurrentUser();
    if (userData) {
        console.log("User data for payments:", userData);
        updateDashboard(userData);
        displayPackages(userData.packages);
        updateBonusDisplay(userData.bonus);
    }
}

// Add real-time polling
function startBalancePolling() {
    // Refresh every 3 seconds for real-time updates
    setInterval(loadUserProfile, 3000);
}

//===========================================================================
//
//   WITHDRAWALS JS
//==============================================================================

document.addEventListener('DOMContentLoaded', function() {
    const withdrawBtn = document.getElementById('withdraw-btn');
    
    if (withdrawBtn) {
        withdrawBtn.addEventListener('click', function(e) {
            e.preventDefault();
            processWithdrawal();
        });
    }

    function processWithdrawal() {
        // Get input values
        const phoneInput = document.getElementById('withdraw-phone');
        const amountInput = document.getElementById('withdraw-amount'); 
        
        const phone = phoneInput ? phoneInput.value.trim() : '';
        const amount = amountInput ? amountInput.value.trim() : '';

        // Validate inputs
        if (!validateInputs(phone, amount)) {
            return;
        }

        // Prepare data for API
        const withdrawalData = {
            phone_number: phone,
            amount: parseInt(amount)
     
        };
        // Send request to Flask backend
        makeWithdrawalRequest(withdrawalData);
    }

    function validateInputs(phone, amount) {
        // Validate phone number
        // const cleanedPhone = phone.replace(/\s+/g, '');
        // const phoneRegex = /^(256|0)(7[0-9]|20)[0-9]{7}$/;
        
        // if (!cleanedPhone) {
        //     alert('Please enter your phone number');
        //     return false;
        // }
        
        // if (!phoneRegex.test(cleanedPhone)) {
        //     alert('Please enter a valid Ugandan phone number (e.g., 256771234567 or 0771234567)');
        //     return false;
        // }

        // Validate amount
        const amountNum = parseInt(amount);
        if (!amount || isNaN(amountNum)) {
            alert('Please enter a valid amount');
            return false;
        }
        
        if (amountNum < 5000) {
            alert('Minimum withdrawal amount is UGX 5,000');
            return false;
        }

        // Check if amount is a whole number
        if (!/^\d+$/.test(amount)) {
            alert('Amount must be a whole number (no decimals)');
            return false;
        }

        return true;
    }

    async function makeWithdrawalRequest(data) {
        // Convert phone to 256 format if it's in local format
        let phoneNumber = data.phone_number;
        // if (phoneNumber.startsWith('0')) {
        //     phoneNumber = '256' + phoneNumber.substring(1);
        // }

        const payload = {
            phone_number: phoneNumber,
            amount: data.amount
   //        
        };

        try {
            // Show loading state
            withdrawBtn.disabled = true;
            withdrawBtn.textContent = 'Processing...';
            console.log("Withdrawal payload:", payload);
            const response = await fetch('/payments/withdraw', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(payload),
              credentials: "include",
            });

            const result = await response.json();

            if (response.ok) {
                // Success case
                alert('Withdrawal initiated successfully! Funds will be processed shortly.');
                // Clear form
                document.getElementById('withdraw-phone').value = '';
                document.getElementById('withdraw-amount').value = '';
                
                // Optionally close modal
                const modal = document.getElementById('modal-withdraw');
                if (modal) modal.style.display = 'none';
            } else {
                // Error case
                alert(`Withdrawal failed: ${result.message || 'Please try again later'}`);
            }

        } catch (error) {
            console.error('Withdrawal error:', error);
            alert('Network error. Please check your connection and try again.');
        } finally {
            // Reset button state
            withdrawBtn.disabled = false;
            withdrawBtn.textContent = 'Withdraw';
        }
    }
});