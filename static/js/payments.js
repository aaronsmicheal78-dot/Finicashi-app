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



































// // --- Event delegation for dynamic modals ---
// document.addEventListener("click", async (event) => {
//   const payButton = event.target.closest(".pay-btn");
//   if (!payButton) return;

//   const modal = payButton.closest(".payment-modal");
//   if (!modal) return;
    
//    //const phoneInput= modal.querySelector(".phone-input");
//    //const amountInput = modal.querySelector(".amount-input");
//   // Extract modal attributes and input
//   let amount = modal.getAttribute("data-amount");
//   const packageName = modal.getAttribute("data-package");
//   const phoneInput = modal.querySelector(".phone-input");
  
//   if (!phoneInput) {
//     alert("Missing phone input field.");
//     return;
//   }



//   const phone = phoneInput.value.trim();

//   // --- Phone validation ---
//   const phoneRegex = /^(?:\+2567|07)\d{8}$/;
//   if (!phone) {
//     alert("Please enter your phone number.");
//     phoneInput.focus();
//     return;
//   }
//   if (!phoneRegex.test(phone)) {
//     alert("Invalid phone number format. Use +2567XXXXXXXX or 07XXXXXXXX.");
//     phoneInput.focus();
//     return;
//   }

//   // --- Determine if deposit ---
//   const isDeposit = packageName?.toLowerCase() === "deposit";

//   // For deposit, override amount from input field if available
//   if (isDeposit) {
//     const inputAmount = parseInt(phoneInput.value, 10); // or use separate deposit input
//     if (!isNaN(inputAmount) && inputAmount > 0) {
//       amount = inputAmount;
//     }
//   }

//   const parsedAmount = parseInt(amount, 10);
//   if (isNaN(parsedAmount) || parsedAmount <= 0) {
//     alert("Invalid payment amount.");
//     return;
//   }

//   // --- Prepare payload ---
//   const payload = {
//     phone: phone,
//     amount: parsedAmount,
//     payment_type: isDeposit ? "deposit" : "package",
//   };
//   if (!isDeposit) payload.package = packageName.toLowerCase();

//   console.log("📦 Payment payload:", payload);

//   // --- Send request ---
//   try {
//     payButton.disabled = true;
//     payButton.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...`;

//     const response = await fetch("/payments/initiate", {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify(payload),
//     });

//     const data = await response.json();

//     if (!response.ok) {
//       console.error("❌ Backend error:", data);
//       alert(data.error || "Payment initiation failed.");
//       return;
//     }

//     if (data.checkout_url) {
//       window.location.href = data.checkout_url;
//     } else {
//       alert("Payment initiated successfully. Please wait for confirmation.");
//     }

//   } catch (err) {
//     console.error("⚠️ Network/server error:", err);
//     alert("Network or server error. Please try again later.");
//   } finally {
//     payButton.disabled = false;
//     payButton.textContent = "Pay Now";
//   }
// });

// payments.js
// document.addEventListener("DOMContentLoaded", () => {
//   const modals = document.querySelectorAll(".payment-modal");

//   modals.forEach((modal) => {
//     const payButton = modal.querySelector(".pay-btn");
//     const phoneInput = modal.querySelector(".phone-input");
//     const amount = modal.getAttribute("data-amount");
//     const packageName = modal.getAttribute("data-package");

//     if (!payButton || !amount || !packageName) {
//       console.warn(`⚠️ Missing configuration in modal: ${modal.id}`);
//       return;
//     }

//     payButton.addEventListener("click", async (e) => {
//       e.preventDefault();

//       // -------------------------------
//       // 🧩 Basic validation
//       // -------------------------------
//       if (!phoneInput || !phoneInput.value.trim()) {
//         alert("Please enter your phone number.");
//         phoneInput?.focus();
//         return;
//       }

//       const phone = phoneInput.value.trim();
//       const phoneRegex = /^(?:\+256|0)?7\d{8}$/;

//       if (!phoneRegex.test(phone)) {
//         alert("Invalid phone number. Use +2567XXXXXXXX or 07XXXXXXXX.");
//         phoneInput.focus();
//         return;
//       }

//       const parsedAmount = parseInt(amount, 10);
//       if (isNaN(parsedAmount) || parsedAmount <= 0) {
//         alert("Invalid payment amount.");
//         return;
//       }

//       // -------------------------------
//       // 💰 Prepare payment payload
//       // -------------------------------
//       const payload = {
//         phone: phone,
//         amount: parsedAmount,
//         type: packageName.toLowerCase() === "deposit" ? "deposit" : "package",
//       };

//       if (payload.type === "package") {
//         payload.package = packageName.toLowerCase();
//       }

//       console.log("🚀 Sending payment payload:", payload);

//       // -------------------------------
//       // 🔄 Send to backend
//       // -------------------------------
//       try {
//         payButton.disabled = true;
//         payButton.textContent = "Processing...";

//         const res = await fetch("/payments/initiate", {
//           method: "POST",
//           headers: { "Content-Type": "application/json" },
//           body: JSON.stringify(payload),
//         });

//         const data = await res.json();

//         if (!res.ok) {
//           console.error("❌ Backend error:", data);
//           alert(data.error || "Payment initiation failed.");
//           return;
//         }

//         console.log("✅ Payment response:", data);

//         if (data.checkout_url) {
//           window.location.href = data.checkout_url;
//         } else {
//           alert("Payment initiated successfully. Please wait for confirmation.");
//         }

//       } catch (err) {
//         console.error("⚠️ Network/server error:", err);
//         alert("Network or server error. Please try again.");
//       } finally {
//         payButton.disabled = false;
//         payButton.textContent = "Pay Now";
//       }
//     });
//   });
// });

// // // payments.js
// document.addEventListener("DOMContentLoaded", () => {
//   // Select all payment modals
//   const modals = document.querySelectorAll(".payment-modal");

//   // Loop through each modal and attach submit listener
//   modals.forEach((modal) => {
//     const payButton = modal.querySelector(".pay-btn");

//     if (!payButton) {
//       console.warn("Pay button missing in modal:", modal.id);
//       return;
//     }

//     payButton.addEventListener("click", async (event) => {
//       event.preventDefault();

//       // Extract modal data attributes
//       const amount = modal.getAttribute("data-amount");
//       const packageName = modal.getAttribute("data-package");
//       const phoneInput = modal.querySelector(".phone-input");

//       // Validate presence of elements
//       if (!amount || !packageName) {
//         alert("Payment configuration error. Please refresh the page.");
//         console.error("Missing data attributes in modal:", modal.id);
//         return;
//       }

//       if (!phoneInput) {
//         alert("Missing phone input field.");
//         return;
//       }

//       const phone = phoneInput.value.trim();

//       // -------------------------------
//       // 1️⃣ Frontend VALIDATION
//       // -------------------------------

//       // Check if phone is provided
//       if (!phone) {
//         alert("Please enter your phone number.");
//         phoneInput.focus();
//         return;
//       }

//       // Basic Ugandan phone number validation
//       const phoneRegex = /^(?:\+256|0)?7\d{8}$/;
//       if (!phoneRegex.test(phone)) {
//         alert("Invalid phone number format. Use +2567XXXXXXXX or 07XXXXXXXX.");
//         phoneInput.focus();
//         return;
//       }

//       // Ensure amount is valid integer
//       const parsedAmount = parseInt(amount);
//       if (isNaN(parsedAmount) || parsedAmount <= 0) {
//         alert("Invalid payment amount.");
//         return;
//       }
    
//       const payload = {
//         amount: parsedAmount,
//         package: packageName.toLowerCase(),
//         phone: phone
//       };
     

//       console.log("Sending payment payload:", payload);

//       try {
    
//         payButton.disabled = true;
//         payButton.textContent = "Processing...";

//         const response = await fetch('/payments/initiate', {
//           method: "POST",
//           headers: {
//             "Content-Type": "application/json",
//           },
//           body: JSON.stringify(payload)
//         });

//         // Parse backend response
//         const data = await response.json();

//         // -------------------------------
//         // 3️⃣ HANDLE RESPONSE
//         // -------------------------------
//         if (!response.ok) {
//           alert(data.error || "Payment initiation failed.");
//           console.error("Backend error:", data);
//           return;
//         }

//         console.log("Payment initiated successfully:", data);

//         // Redirect if checkout URL is provided (from MarzPay or gateway)
//         if (data.checkout_url) {
//           window.location.href = data.checkout_url;
//         } else {
//           // No redirect — backend will confirm async
//           alert("Payment initiated successfully. Please wait for confirmation.");
//         }

//       } catch (error) {
//         // -------------------------------
//         // 4️⃣ HANDLE NETWORK ERRORS
//         // -------------------------------
//         console.error("Network or server error:", error);
//         alert("Network or server error. Please try again later.");
//       }
//     });
//   });
// });



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
            amount: parseInt(amount),
            narration: 'Cash Out - Finicashi'
        };
        // Send request to Flask backend
        makeWithdrawalRequest(withdrawalData);
    }

    function validateInputs(phone, amount) {
        // Validate phone number
        const cleanedPhone = phone.replace(/\s+/g, '');
        const phoneRegex = /^(256|0)(7[0-9]|20)[0-9]{7}$/;
        
        if (!cleanedPhone) {
            alert('Please enter your phone number');
            return false;
        }
        
        if (!phoneRegex.test(cleanedPhone)) {
            alert('Please enter a valid Ugandan phone number (e.g., 256771234567 or 0771234567)');
            return false;
        }

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
        if (phoneNumber.startsWith('0')) {
            phoneNumber = '256' + phoneNumber.substring(1);
        }

        const payload = {
            phone_number: phoneNumber,
            amount: data.amount,
            narration: data.narration
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