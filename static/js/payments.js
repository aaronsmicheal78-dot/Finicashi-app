
// // payments.js
// document.addEventListener("DOMContentLoaded", () => {
//   // Select all package cards instead of modals
//   const packageCards = document.querySelectorAll(".package-card");

//   packageCards.forEach((card) => {
//     const investButton = card.querySelector(".package-btn");

//     if (!investButton) {
//       console.warn("Invest button missing in package card:", card);
//       return;
//     }

//     investButton.addEventListener("click", async (event) => {
//       event.preventDefault();

//       // Extract data from the PACKAGE CARD (not modal)
//       const amount = card.getAttribute("data-amount");
//       const packageName = card.getAttribute("data-package");
//       const modalId = card.getAttribute("data-modal");

//       console.log("Package card data:", { amount, packageName, modalId });

//       // Find the corresponding modal
//       const modal = document.getElementById(modalId);
//       if (!modal) {
//         console.error("Modal not found:", modalId);
//         alert("Modal not found. Please refresh the page.");
//         return;
//       }

//       // Show the modal first
//       modal.style.display = "block";

//       // Wait for modal to be visible, then attach payment handler
//       setTimeout(() => {
//         attachPaymentHandler(modal, amount, packageName);
//       }, 100);
//     });
//   });

//   // Function to handle payment when modal is open
//   function attachPaymentHandler(modal, amount, packageName) {
//     const payButton = modal.querySelector(".pay-btn");
//     const phoneInput = modal.querySelector(".phone-input");
//     const closeButton = modal.querySelector(".close-modal");

//     if (!payButton || !phoneInput) {
//       console.error("Missing elements in modal:", modal.id);
//       return;
//     }

//     // Remove any existing click handlers
//     payButton.replaceWith(payButton.cloneNode(true));
//     const newPayButton = modal.querySelector(".pay-btn");

//     newPayButton.addEventListener("click", async (event) => {
//       event.preventDefault();

//       const phone = phoneInput.value.trim();

//       // Validation
//       if (!phone) {
//         alert("Please enter your phone number.");
//         phoneInput.focus();
//         return;
//       }

//       const phoneRegex = /^(?:\+256|0)?7\d{8}$/;
//       if (!phoneRegex.test(phone)) {
//         alert("Invalid phone number format. Use +2567XXXXXXXX or 07XXXXXXXX.");
//         phoneInput.focus();
//         return;
//       }

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
//         newPayButton.disabled = true;
//         newPayButton.textContent = "Processing...";

//         const response = await fetch("/payments/initiate/", {
//           method: "POST",
//           headers: {
//             "Content-Type": "application/json",
//           },
//           body: JSON.stringify(payload)
//         });

//         const data = await response.json();

//         if (!response.ok) {
//           alert(data.error || "Payment initiation failed.");
//           console.error("Backend error:", data);
//           return;
//         }

//         console.log("Payment initiated successfully:", data);

//         if (data.checkout_url) {
//           window.location.href = data.checkout_url;
//         } else {
//           alert("Payment initiated successfully. Please wait for confirmation.");
//           // Close modal on success
//           modal.style.display = "none";
//         }

//       } catch (error) {
//         console.error("Network or server error:", error);
//         alert("Network or server error. Please try again later.");
//       } finally {
//         newPayButton.disabled = false;
//         newPayButton.textContent = "Pay Now";
//       }
//     });

//     // Close modal handler
//     if (closeButton) {
//       closeButton.addEventListener("click", () => {
//         modal.style.display = "none";
//       });
//     }

//     // Close modal when clicking outside
//     modal.addEventListener("click", (e) => {
//       if (e.target === modal) {
//         modal.style.display = "none";
//       }
//     });
//   }
// });
// // // payments.js - SIMPLER VERSION
// // document.addEventListener("DOMContentLoaded", () => {
// //   // Handle package card clicks to show modals
// //   document.querySelectorAll(".package-btn").forEach(button => {
// //     button.addEventListener("click", function() {
// //       const card = this.closest(".package-card");
// //       const modalId = card.getAttribute("data-modal");
// //       const modal = document.getElementById(modalId);
      
// //       if (modal) {
// //         modal.style.display = "block";
        
// //         // Store package data in modal for payment button
// //         modal.setAttribute("data-current-package", card.getAttribute("data-package"));
// //         modal.setAttribute("data-current-amount", card.getAttribute("data-amount"));
// //       }
// //     });
// //   });

// //   // Handle payment button clicks
// //   document.querySelectorAll(".pay-btn").forEach(button => {
// //     button.addEventListener("click", async function() {
// //       const modal = this.closest(".payment-modal");
// //       const amount = modal.getAttribute("data-current-amount");
// //       const packageName = modal.getAttribute("data-current-package");
// //       const phoneInput = modal.querySelector(".phone-input");
      
// //       if (!amount || !packageName) {
// //         alert("Package data missing. Please try again.");
// //         return;
// //       }

// //       const phone = phoneInput.value.trim();
      
// //       // Validation
// //       if (!phone) {
// //         alert("Please enter your phone number.");
// //         phoneInput.focus();
// //         return;
// //       }

// //       const phoneRegex = /^(?:\+256|0)?7\d{8}$/;
// //       if (!phoneRegex.test(phone)) {
// //         alert("Invalid phone number format. Use +2567XXXXXXXX or 07XXXXXXXX.");
// //         phoneInput.focus();
// //         return;
// //       }

// //       const payload = {
// //         amount: parseInt(amount),
// //         package: packageName.toLowerCase(),
// //         phone: phone
// //       };

// //       console.log("Sending payload:", payload);

// //       try {
// //         this.disabled = true;
// //         this.textContent = "Processing...";

// //         const response = await fetch("/payments/initiate/", {
// //           method: "POST",
// //           headers: { "Content-Type": "application/json" },
// //           body: JSON.stringify(payload)
// //         });

// //         const data = await response.json();

// //         if (!response.ok) {
// //           throw new Error(data.error || "Payment failed");
// //         }

// //         alert("Payment initiated successfully!");
// //         console.log("Success:", data);
        
// //         if (data.checkout_url) {
// //           window.location.href = data.checkout_url;
// //         } else {
// //           modal.style.display = "none";
// //         }

// //       } catch (error) {
// //         alert(error.message);
// //         console.error("Error:", error);
// //       } finally {
// //         this.disabled = false;
// //         this.textContent = "Pay Now";
// //       }
// //     });
// //   });

// //   // Close modals
// //   document.querySelectorAll(".close-modal").forEach(button => {
// //     button.addEventListener("click", function() {
// //       this.closest(".modal").style.display = "none";
// //     });
// //   });
// // });
// payments.js
document.addEventListener("DOMContentLoaded", () => {
  // Select all payment modals
  const modals = document.querySelectorAll(".payment-modal");

  // Loop through each modal and attach submit listener
  modals.forEach((modal) => {
    const payButton = modal.querySelector(".pay-btn");

    if (!payButton) {
      console.warn("Pay button missing in modal:", modal.id);
      return;
    }

    payButton.addEventListener("click", async (event) => {
      event.preventDefault();

      // Extract modal data attributes
      const amount = modal.getAttribute("data-amount");
      const packageName = modal.getAttribute("data-package");
      const phoneInput = modal.querySelector(".phone-input");

      // Validate presence of elements
      if (!amount || !packageName) {
        alert("Payment configuration error. Please refresh the page.");
        console.error("Missing data attributes in modal:", modal.id);
        return;
      }

      if (!phoneInput) {
        alert("Missing phone input field.");
        return;
      }

      const phone = phoneInput.value.trim();

      // -------------------------------
      // 1️⃣ Frontend VALIDATION
      // -------------------------------

      // Check if phone is provided
      if (!phone) {
        alert("Please enter your phone number.");
        phoneInput.focus();
        return;
      }

      // Basic Ugandan phone number validation
      const phoneRegex = /^(?:\+256|0)?7\d{8}$/;
      if (!phoneRegex.test(phone)) {
        alert("Invalid phone number format. Use +2567XXXXXXXX or 07XXXXXXXX.");
        phoneInput.focus();
        return;
      }

      // Ensure amount is valid integer
      const parsedAmount = parseInt(amount);
      if (isNaN(parsedAmount) || parsedAmount <= 0) {
        alert("Invalid payment amount.");
        return;
      }
    
      const payload = {
        amount: parsedAmount,
        package: packageName.toLowerCase(),
        phone: phone
      };
     
      console.log("Sending payment payload:", payload);

      try {
    
        payButton.disabled = true;
        payButton.textContent = "Processing...";

        const response = await fetch("/payments/withdraw", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload)
        });

        // Parse backend response
        const data = await response.json();

        // -------------------------------
        // 3️⃣ HANDLE RESPONSE
        // -------------------------------
        if (!response.ok) {
          alert(data.error || "Payment initiation failed.");
          console.error("Backend error:", data);
          return;
        }

        console.log("Payment initiated successfully:", data);

        // Redirect if checkout URL is provided (from MarzPay or gateway)
        if (data.checkout_url) {
          window.location.href = data.checkout_url;
        } else {
          // No redirect — backend will confirm async
          alert("Payment initiated successfully. Please wait for confirmation.");
        }

      } catch (error) {
        // -------------------------------
        // 4️⃣ HANDLE NETWORK ERRORS
        // -------------------------------
        console.error("Network or server error:", error);
        alert("Network or server error. Please try again later.");
      }
    });
  });
});



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