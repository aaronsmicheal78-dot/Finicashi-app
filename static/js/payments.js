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
    setInterval(loadUserProfile, 5000);
}

//===========================================================================
//
//   WITHDRAWALS JS
//==============================================================================
// withdraw.js - Professional Withdrawal Handler with Full Error Display

class WithdrawalHandler {
    constructor() {
        this.initializeElements();
        this.attachEventListeners();
        this.setupRealTimeValidation();
    }

    initializeElements() {
        // Form elements
        this.phoneInput = document.getElementById('withdraw-phone');
        this.amountInput = document.getElementById('withdraw-amount');
        this.withdrawBtn = document.getElementById('withdraw-btn');
        
        // Message containers
        this.createMessageContainer();
        
        // Balance display (if exists)
        this.balanceElements = {
            actual: document.getElementById('actual-balance'),
            wallet: document.getElementById('wallet-balance'),
            total: document.getElementById('total-balance')
        };
        
        // Modal elements
        this.modal = document.getElementById('modal-withdraw');
    }

    createMessageContainer() {
        // Remove existing if any
        const existingContainer = document.getElementById('withdraw-message-container');
        if (existingContainer) existingContainer.remove();
        
        // Create message container near the form
        const form = document.querySelector('#withdraw-form') || 
                    document.querySelector('.withdraw-form') ||
                    document.getElementById('withdraw-btn')?.closest('form');
        
        if (form) {
            const container = document.createElement('div');
            container.id = 'withdraw-message-container';
            container.className = 'withdraw-message-container';
            form.insertBefore(container, form.firstChild);
            this.messageContainer = container;
        } else {
            // Fallback - create after withdraw button
            const btn = this.withdrawBtn;
            if (btn) {
                const container = document.createElement('div');
                container.id = 'withdraw-message-container';
                container.className = 'withdraw-message-container';
                btn.parentNode.insertBefore(container, btn.nextSibling);
                this.messageContainer = container;
            }
        }
    }

    attachEventListeners() {
        if (this.withdrawBtn) {
            this.withdrawBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.processWithdrawal();
            });
        }
        
        // Close modal when clicking outside
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.closeModal();
                }
            });
        }
    }

    setupRealTimeValidation() {
        // Real-time amount validation
        if (this.amountInput) {
            this.amountInput.addEventListener('input', () => this.validateAmountRealtime());
            this.amountInput.addEventListener('blur', () => this.validateAmountRealtime());
        }
        
        // Real-time phone validation
        if (this.phoneInput) {
            this.phoneInput.addEventListener('input', () => this.validatePhoneRealtime());
            this.phoneInput.addEventListener('blur', () => this.validatePhoneRealtime());
        }
    }

    validateAmountRealtime() {
        if (!this.amountInput) return;
        
        const amount = this.amountInput.value.trim();
        const amountNum = parseInt(amount);
        const errorSpan = this.getFieldErrorSpan('amount');
        
        if (!amount) {
            this.clearFieldError('amount');
            return;
        }
        
        if (isNaN(amountNum)) {
            this.showFieldError('amount', 'Please enter a valid number');
        } else if (amountNum < 5000) {
            this.showFieldError('amount', 'Minimum withdrawal is UGX 5,000');
        } else if (amountNum > 100000) {
            this.showFieldError('amount', 'Maximum withdrawal is UGX 100,000');
        } else {
            this.clearFieldError('amount');
        }
    }

    validatePhoneRealtime() {
        if (!this.phoneInput) return;
        
        const phone = this.phoneInput.value.trim();
        
        if (!phone) {
            this.clearFieldError('phone');
            return;
        }
        
        // Validate Uganda phone number
        const ugPhoneRegex = /^(?:0|256)?[7-9][0-9]{8}$/;
        if (!ugPhoneRegex.test(phone)) {
            this.showFieldError('phone', 'Enter a valid Uganda phone number (e.g., 0768732708)');
        } else {
            this.clearFieldError('phone');
        }
    }

    getFieldErrorSpan(field) {
        let errorSpan = document.getElementById(`error-${field}`);
        if (!errorSpan) {
            const input = field === 'amount' ? this.amountInput : this.phoneInput;
            if (input && input.parentNode) {
                errorSpan = document.createElement('span');
                errorSpan.id = `error-${field}`;
                errorSpan.className = 'field-error';
                input.parentNode.insertBefore(errorSpan, input.nextSibling);
            }
        }
        return errorSpan;
    }

    showFieldError(field, message) {
        const errorSpan = this.getFieldErrorSpan(field);
        if (errorSpan) {
            errorSpan.textContent = message;
            errorSpan.style.display = 'block';
        }
        
        // Add error class to input
        const input = field === 'amount' ? this.amountInput : this.phoneInput;
        if (input) input.classList.add('input-error');
    }

    clearFieldError(field) {
        const errorSpan = this.getFieldErrorSpan(field);
        if (errorSpan) {
            errorSpan.textContent = '';
            errorSpan.style.display = 'none';
        }
        
        const input = field === 'amount' ? this.amountInput : this.phoneInput;
        if (input) input.classList.remove('input-error');
    }

    async processWithdrawal() {
        // Clear previous messages
        this.clearMessages();
        
        // Get input values
        const phone = this.phoneInput ? this.phoneInput.value.trim() : '';
        const amount = this.amountInput ? this.amountInput.value.trim() : '';

        // Validate inputs
        if (!this.validateInputs(phone, amount)) {
            return;
        }

        // Format phone number to 256 format
        const formattedPhone = this.formatPhoneNumber(phone);
        
        const withdrawalData = {
            phone_number: formattedPhone,
            amount: parseInt(amount)
        };

        await this.makeWithdrawalRequest(withdrawalData);
    }

    formatPhoneNumber(phone) {
        // Already in 256 format
        if (phone.startsWith('256')) return phone;
        // Starts with 0
        if (phone.startsWith('0')) return '256' + phone.substring(1);
        // Already valid
        return phone;
    }

    validateInputs(phone, amount) {
        let isValid = true;
        
        // Validate phone
        if (!phone) {
            this.showMessage('Phone number is required', 'error');
            isValid = false;
        } else {
            const ugPhoneRegex = /^(?:0|256)?[7-9][0-9]{8}$/;
            if (!ugPhoneRegex.test(phone)) {
                this.showMessage('Please enter a valid Uganda phone number', 'error');
                isValid = false;
            }
        }

        // Validate amount
        const amountNum = parseInt(amount);
        if (!amount || isNaN(amountNum)) {
            this.showMessage('Please enter a valid amount', 'error');
            isValid = false;
        } else if (amountNum < 5000) {
            this.showMessage('Minimum withdrawal amount is UGX 5,000', 'error');
            isValid = false;
        } else if (amountNum > 100000) {
            this.showMessage('Maximum withdrawal amount is UGX 100,000', 'error');
            isValid = false;
        } else if (!/^\d+$/.test(amount)) {
            this.showMessage('Amount must be a whole number (no decimals)', 'error');
            isValid = false;
        }

        return isValid;
    }

    async makeWithdrawalRequest(data) {
        // Show loading state
        this.setLoading(true);
        
        const idempotencyKey = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        try {
            const response = await fetch('/payments/withdraw', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Idempotency-Key': idempotencyKey
                },
                body: JSON.stringify(data),
                credentials: "include",
            });

            const result = await response.json();

            if (response.ok && result.success) {
                // Handle success
                this.handleSuccess(result);
            } else {
                // Handle error with backend message
                this.handleError(result, response.status);
            }

        } catch (error) {
            console.error('Withdrawal error:', error);
            this.showMessage(
                'Network error. Please check your connection and try again.',
                'error'
            );
        } finally {
            this.setLoading(false);
        }
    }

    handleSuccess(result) {
        // Show success message with details
        const successMsg = result.message || 'Withdrawal initiated successfully!';
        const data = result.data || {};
        
        this.showMessage(
            `<div class="success-content">
                <div class="success-icon">✅</div>
                <div class="success-text">
                    <strong>${successMsg}</strong>
                    ${data.reference ? `<br>Reference: ${data.reference}` : ''}
                    ${data.net_amount ? `<br>Net Amount: UGX ${this.formatMoney(data.net_amount)}` : ''}
                    ${data.fee ? `<br>Processing Fee: UGX ${this.formatMoney(data.fee)}` : ''}
                </div>
            </div>`,
            'success'
        );
        
        // Clear form
        if (this.phoneInput) this.phoneInput.value = '';
        if (this.amountInput) this.amountInput.value = '';
        
        // Close modal if open
        this.closeModal();
        
        // Update balance display if function exists
        if (typeof window.updateBalances === 'function') {
            window.updateBalances();
        }
        
        // Optional: Show success modal with more details
        this.showSuccessModal(result);
    }

    handleError(result, statusCode) {
        const errorType = result.error_type || 'general';
        const errorMessage = result.error || result.message || 'Withdrawal failed. Please try again.';
        const context = result.user_context || {};
        
        // Display appropriate UI based on error type
        switch(errorType) {
            case 'WALLET_HOLD':
                this.showWalletHoldError(errorMessage, context, result.error_data);
                break;
            case 'INSUFFICIENT_BALANCE':
                this.showInsufficientBalanceError(errorMessage, context);
                break;
            case 'RATE_LIMIT':
                this.showRateLimitError(errorMessage, result.error_data);
                break;
            case 'MIN_AMOUNT':
                this.showMinAmountError(errorMessage, result.error_data);
                break;
            case 'MAX_AMOUNT':
                this.showMaxAmountError(errorMessage, result.error_data);
                break;
            case 'PENDING_EXISTS':
                this.showPendingError(errorMessage);
                break;
            case 'INVALID_PHONE':
                this.showPhoneError(errorMessage);
                break;
            case 'ACCOUNT_NOT_VERIFIED':
                this.showVerificationError(errorMessage);
                break;
            case 'ACCOUNT_INACTIVE':
                this.showInactiveAccountError(errorMessage);
                break;
            default:
                this.showMessage(errorMessage, 'error');
        }
    }

    showWalletHoldError(message, context, errorData) {
        const actualBalance = context.actual_balance || 0;
        const walletBalance = context.wallet_balance || 0;
        const availableNow = context.actual_balance || 0;
        
        const modalContent = `
            <div class="modal-header">
                <h3>⏰ Wallet Funds on Hold</h3>
                <button class="modal-close" onclick="withdrawalHandler.closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <p>${message}</p>
                
                <div class="balance-breakdown">
                    <div class="balance-item">
                        <span>💰 Actual Balance:</span>
                        <strong>UGX ${this.formatMoney(actualBalance)}</strong>
                        <small>(Available now)</small>
                    </div>
                    <div class="balance-item muted">
                        <span>⏳ Wallet Balance:</span>
                        <strong>UGX ${this.formatMoney(walletBalance)}</strong>
                        <small>(24-hour hold)</small>
                    </div>
                    <div class="balance-item total">
                        <span>💵 Total Available Now:</span>
                        <strong>UGX ${this.formatMoney(availableNow)}</strong>
                    </div>
                </div>
                
                <div class="info-box">
                    <strong>💡 What does this mean?</strong>
                    <ul>
                        <li>Your <strong>Actual Balance</strong> is from direct deposits and available immediately</li>
                        <li>Your <strong>Wallet Balance</strong> is from bonuses and requires a 24-hour security hold</li>
                        <li>You can withdraw your actual balance right now</li>
                    </ul>
                </div>
                
                <div class="action-buttons">
                    <button class="btn-primary" onclick="withdrawalHandler.withdrawOnlyActual()">
                        💰 Withdraw UGX ${this.formatMoney(actualBalance)}
                    </button>
                    <button class="btn-secondary" onclick="withdrawalHandler.closeModal()">
                        Wait for Wallet Funds
                    </button>
                </div>
            </div>
        `;
        
        this.showModal(modalContent);
    }

    showInsufficientBalanceError(message, context) {
        const totalBalance = context.total_balance || 0;
        
        const modalContent = `
            <div class="modal-header">
                <h3>💰 Insufficient Balance</h3>
                <button class="modal-close" onclick="withdrawalHandler.closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <p>${message}</p>
                
                <div class="balance-card">
                    <div class="balance-item">
                        <span>Your Total Balance:</span>
                        <strong>UGX ${this.formatMoney(totalBalance)}</strong>
                    </div>
                </div>
                
                <div class="action-buttons">
                    <button class="btn-primary" onclick="withdrawalHandler.setMaxAmount(${totalBalance})">
                        Withdraw UGX ${this.formatMoney(totalBalance)}
                    </button>
                    <button class="btn-secondary" onclick="withdrawalHandler.closeModal()">
                        Cancel
                    </button>
                </div>
            </div>
        `;
        
        this.showModal(modalContent);
    }

    showRateLimitError(message, errorData) {
        const dailyLimit = errorData?.daily_limit || 3;
        
        this.showMessage(
            `<div class="error-content">
                <strong>⏰ Daily Limit Reached</strong><br>
                ${message}<br>
                <small>Maximum ${dailyLimit} withdrawals per day. Please try again tomorrow.</small>
            </div>`,
            'error'
        );
    }

    showMinAmountError(message, errorData) {
        const minAmount = errorData?.min_amount || 5000;
        
        this.showMessage(
            `<div class="error-content">
                <strong>⚠️ Amount Too Low</strong><br>
                ${message}<br>
                <button class="btn-small" onclick="withdrawalHandler.setMinAmount(${minAmount})">
                    Use Minimum (UGX ${this.formatMoney(minAmount)})
                </button>
            </div>`,
            'error'
        );
    }

    showMaxAmountError(message, errorData) {
        const maxAmount = errorData?.max_amount || 100000;
        
        this.showMessage(
            `<div class="error-content">
                <strong>⚠️ Amount Too High</strong><br>
                ${message}<br>
                <small>Maximum per transaction: UGX ${this.formatMoney(maxAmount)}</small>
            </div>`,
            'error'
        );
    }

    showPendingError(message) {
        this.showMessage(
            `<div class="error-content">
                <strong>⏳ Pending Withdrawal.</strong><br>
                ${message}<br>
                <small>Please wait for your current withdrawal to complete before requesting another.</small>
            </div>`,
            'warning'
        );
    }

    showPhoneError(message) {
        this.showMessage(
            `<div class="error-content">
                <strong>📱 Enter correct Phone number that is in system</strong><br>
                ${message}<br>
             
            </div>`,
            'error'
        );
    }

    showVerificationError(message) {
        this.showMessage(
            `<div class="error-content">
                <strong>🔒 Account Not Verified. please Verify!</strong><br>
                ${message}<br>
               
            </div>`,
            'error'
        );
    }

    showInactiveAccountError(message) {
        this.showMessage(
            `<div class="error-content">
                <strong>🚫 Account Inactive. Contact Admin</strong><br>
                ${message}<br>
              
            </div>`,
            'error'
        );
    }

    withdrawOnlyActual() {
        const actualBalanceElem = document.getElementById('actual-balance');
        if (actualBalanceElem && this.amountInput) {
            const balance = actualBalanceElem.dataset.value || actualBalanceElem.textContent;
            const amount = parseInt(balance.replace(/[^0-9]/g, ''));
            if (amount > 0) {
                this.amountInput.value = amount;
                this.processWithdrawal();
            }
        }
        this.closeModal();
    }

    setMaxAmount(amount) {
        if (this.amountInput && amount > 0) {
            this.amountInput.value = amount;
            this.closeModal();
            this.processWithdrawal();
        }
    }

    setMinAmount(amount) {
        if (this.amountInput && amount > 0) {
            this.amountInput.value = amount;
            this.processWithdrawal();
        }
    }

    showSuccessModal(result) {
        const data = result.data || {};
        
        const modalContent = `
            <div class="modal-header success">
                <h3>✅ Withdrawal Initiated!</h3>
                <button class="modal-close" onclick="withdrawalHandler.closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="success-animation">✅</div>
                <p class="success-message">Your withdrawal request has been submitted successfully!</p>
                
                <div class="transaction-details">
                    <div class="detail-row">
                        <span>Reference:</span>
                        <strong>${data.reference || 'N/A'}</strong>
                    </div>
                    <div class="detail-row">
                        <span>Amount:</span>
                        <strong>UGX ${this.formatMoney(data.net_amount || 0)}</strong>
                    </div>
                    <div class="detail-row">
                        <span>Fee:</span>
                        <strong>UGX ${this.formatMoney(data.fee || 0)}</strong>
                    </div>
                    <div class="detail-row">
                        <span>Status:</span>
                        <span class="status-badge processing">Processing</span>
                    </div>
                </div>
                
                <p class="note">You will receive an SMS confirmation once completed.</p>
                
                <div class="action-buttons">
                    <button class="btn-secondary" onclick="withdrawalHandler.closeModal()">
                        Close
                    </button>
                </div>
            </div>
        `;
        
        this.showModal(modalContent);
        
        // Auto close after 5 seconds
        setTimeout(() => {
            this.closeModal();
        }, 5000);
    }

    showModal(content) {
        // Remove existing modal
        this.closeModal();
        
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'withdrawal-modal';
        modal.id = 'withdrawal-custom-modal';
        modal.innerHTML = `<div class="withdrawal-modal-content">${content}</div>`;
        
        document.body.appendChild(modal);
        modal.style.display = 'flex';
        
        // Store reference
        this.currentModal = modal;
    }

    closeModal() {
        if (this.currentModal) {
            this.currentModal.remove();
            this.currentModal = null;
        }
        
        // Also close original modal if exists
        if (this.modal) {
            this.modal.style.display = 'none';
        }
    }

    showMessage(message, type = 'info') {
        if (!this.messageContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `withdraw-message withdraw-message-${type}`;
        messageDiv.innerHTML = `
            <div class="message-content">
                ${message}
            </div>
            <button class="message-close" onclick="this.parentElement.remove()">&times;</button>
        `;
        
        this.messageContainer.appendChild(messageDiv);
        
        // Auto remove after 8 seconds for non-modal messages
        if (type !== 'modal') {
            setTimeout(() => {
                if (messageDiv.parentElement) {
                    messageDiv.remove();
                }
            }, 20000);
        }
        
        // Scroll to message
        messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    clearMessages() {
        if (this.messageContainer) {
            this.messageContainer.innerHTML = '';
        }
    }

    setLoading(loading) {
        if (this.withdrawBtn) {
            this.withdrawBtn.disabled = loading;
            this.withdrawBtn.innerHTML = loading ? 
                '<span class="spinner"></span> Processing...' : 
                'Withdraw';
        }
    }

    formatMoney(amount) {
        if (!amount && amount !== 0) return '0';
        return parseFloat(amount).toLocaleString('en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }
}

// Initialize on page load
let withdrawalHandler;
document.addEventListener('DOMContentLoaded', function() {
    withdrawalHandler = new WithdrawalHandler();
});
