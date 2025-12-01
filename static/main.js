
        // 
        
    const backgroundImages = [
            'https://www.mountaingorillalodge.com/wp-content/uploads/2025/05/Currency-bann.avif',
            'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80',
            'https://www.independent.co.ug/wp-content/uploads/2017/10/american_money.jpg',
            'https://images.unsplash.com/photo-1640340434855-6084b1f4901c?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1964&q=80',
            'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80',
            'https://www.ceo.co.ug/wp-content/uploads/2020/04/uganda-currency.jpg',
             'https://images.unsplash.com/photo-1460925895917-afdab827c52f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2015&q=80',
             'https://images.unsplash.com/photo-1502920917128-1aa500764cbd?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80'
        ];

        // Initialize background slideshow
       class HeroBackground {
    constructor() {
        this.currentSlide = 0;
        this.slides = document.querySelectorAll('.background-slide');
        this.init();
    }

    init() {
        // Only set images for existing slides
        this.slides.forEach((slide, index) => {
            if (backgroundImages[index]) {
                slide.style.backgroundImage = `url(${backgroundImages[index]})`;
            }
        });

        // Start slideshow
        this.startSlideshow();
    }

    startSlideshow() {
        setInterval(() => {
            this.nextSlide();
        }, 5000);
    }

    nextSlide() {
        // Hide current slide
        this.slides[this.currentSlide].classList.remove('active');
        
        // Move to next slide
        this.currentSlide = (this.currentSlide + 1) % this.slides.length;
        
        // Show next slide
        this.slides[this.currentSlide].classList.add('active');
    }
}
    document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM loaded - initializing auth system");

    // Get all required elements
    const loginModal = document.getElementById('loginModal');
    const loginModalOverlay = document.getElementById('loginModalOverlay');
    const loginModalBtn = document.getElementById('login-modal-btn');
    const registerBtn = document.getElementById('register-btn');
    const loginCloseBtn = document.querySelector('.login-close');
    const loadingPage = document.getElementById('loadingPage');
    
    // Form elements
    const modalLoginForm = document.querySelector('#loginModalOverlay form');
    const authLoginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const switchRegister = document.getElementById('switch-register');
    const switchLogin = document.getElementById('switch-login');
    const loginFormElement = document.getElementById('login-form');



    // 3. REGISTER BUTTON CLICK HANDLER
    if (registerBtn) {
        registerBtn.addEventListener('click', () => {
            console.log("Register button clicked - showing auth form");
            // Scroll to auth container or show it
            document.getElementById('auth-container').scrollIntoView({ 
                behavior: 'smooth' 
            });
        });
    }

// 6. REGISTER FUNCTIONALITY
function handleRegister(event) {
    event.preventDefault();
    console.log("Register form submitted");

    // Get form values
    const fullName = document.getElementById("hero-full-name").value.trim();
    const email = document.getElementById("hero-email").value.trim();
    const phone = document.getElementById("hero-phone").value.trim();
    const referralCode = document.getElementById("hero-code").value.trim();
    const password = document.getElementById("hero-password").value;
    const confirmPassword = document.getElementById("hero-confirm-password").value;

    // Get the submit button for loading state
    const submitButton = event.target.querySelector('button[type="submit"]');

    // Validate required fields
    if (!fullName || !email || !phone || !password || !confirmPassword) {
        showAlert("Please fill in all required fields.", "error");
        return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showAlert("Please enter a valid email address.", "error");
        return;
    }

    // Validate phone (basic - at least 10 digits)
    const phoneRegex = /^[0-9]{10,15}$/;
    if (!phoneRegex.test(phone.replace(/\D/g, ''))) {
        showAlert("Please enter a valid phone number (10-15 digits).", "error");
        return;
    }

    // Validate password match
    if (password !== confirmPassword) {
        showAlert("Passwords do not match. Please re-enter your password.", "error");
        return;
    }

    // Validate password length
    if (password.length < 6) {
        showAlert("Password must be at least 6 characters long.", "error");
        return;
    }

    // Show loading state on button
    if (submitButton) {
        submitButton.textContent = "Creating Account...";
        submitButton.disabled = true;
        submitButton.style.opacity = "0.7";
    }

    // Show loading page
    const loadingPage = document.getElementById("loadingPage");
    if (loadingPage) {
        loadingPage.style.display = "flex";
    }

    // Prepare registration data
    const registerData = {
        fullName: fullName,
        email: email,
        phone: phone,
        referralCode: referralCode || null,
        password: password
    };

    console.log("Sending registration request:", registerData);

    // Send POST request to /api/register
    fetch("/api/signup", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(registerData),
    })
    .then(response => {
        console.log("Registration response status:", response.status);
        
        if (!response.ok) {
            // Try to parse error response as JSON first
            return response.json().then(errorData => {
                // If we get JSON error response, throw with server message
                throw new Error(errorData.message || `Server error: ${response.status}`);
            }).catch(() => {
                // If JSON parsing fails, throw with status-based message
                if (response.status === 400) {
                    throw new Error("Please check your input data and try again.");
                } else if (response.status === 409) {
                    throw new Error("An account with this email or phone already exists.");
                } else if (response.status === 500) {
                    throw new Error("Server error. Please try again later.");
                } else {
                    throw new Error(`Registration failed. Please try again. (Error: ${response.status})`);
                }
            });
        }
        return response.json();
    })
    .then(data => {
        console.log("Registration successful, response data:", data);
        
        if (data.success) {
            showAlert("Registration successful! Welcome to Finicashi. Redirecting...", "success");
           //     if (data.success || response.status === 201) {
        //showAlert("Registration successful! Welcome to Finicashi. Redirecting...", "success");
            
            // Redirect after successful registration
            setTimeout(() => {
                window.location.href = "/profile";
            }, 2000);
        } else {
            // Handle case where response is ok but success is false
            showAlert("Registration completed. Please Login.", "warning");
            
            // Reset button state
            if (submitButton) {
                submitButton.textContent = "Create Account";
                submitButton.disabled = false;
                submitButton.style.opacity = "1";
            }
            
            // Hide loading page
            if (loadingPage) {
                loadingPage.style.display = "none";
            }
        }
    })
    .catch(error => {
        console.error("Registration error:", error);
        
        // Show appropriate error message based on error type
        if (error.message.includes("already exists")) {
            showAlert("An account with this email or phone already exists. Please login instead.", "error");
        } else if (error.message.includes("check your input")) {
            showAlert("Please check your information and try again.", "error");
        } else if (error.message.includes("Server error") || error.message.includes("failed")) {
            showAlert(error.message, "error");
        } else if (error.name === "TypeError" && error.message.includes("fetch")) {
            showAlert("Network error. Please check your connection and try again.", "error");
        } else {
            showAlert("Registration failed. Please try again.", "error");
        }
        
        // Reset button state
        if (submitButton) {
            submitButton.textContent = "Create Account";
            submitButton.disabled = false;
            submitButton.style.opacity = "1";
        }
        
        // Hide loading page
        if (loadingPage) {
            loadingPage.style.display = "none";
        }
    });
}

// Alert display function
function showAlert(message, type = "info") {
    // Remove any existing alerts first
    const existingAlert = document.querySelector('.custom-alert');
    if (existingAlert) {
        existingAlert.remove();
    }

    // Create alert element
    const alert = document.createElement('div');
    alert.className = `custom-alert custom-alert-${type}`;
    alert.innerHTML = `
        <div class="alert-content">
            <span class="alert-message">${message}</span>
            <button class="alert-close">&times;</button>
        </div>
    `;

    // Add styles if not already added
    if (!document.querySelector('#alert-styles')) {
        const styles = document.createElement('style');
        styles.id = 'alert-styles';
        styles.textContent = `
            .custom-alert {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                min-width: 300px;
                max-width: 500px;
                padding: 15px 20px;
                border-radius: 8px;
                color: white;
                font-family: Arial, sans-serif;
                font-size: 14px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                animation: slideIn 0.3s ease-out;
            }
            .custom-alert-success {
                background-color: #10b981;
                border-left: 4px solid #059669;
            }
            .custom-alert-error {
                background-color: #ef4444;
                border-left: 4px solid #dc2626;
            }
            .custom-alert-warning {
                background-color: #f59e0b;
                border-left: 4px solid #d97706;
            }
            .custom-alert-info {
                background-color: #3b82f6;
                border-left: 4px solid #2563eb;
            }
            .alert-content {
                display: flex;
                justify-content: between;
                align-items: center;
            }
            .alert-message {
                flex: 1;
                margin-right: 10px;
            }
            .alert-close {
                background: none;
                border: none;
                color: white;
                font-size: 18px;
                cursor: pointer;
                padding: 0;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(styles);
    }

    // Add to page
    document.body.appendChild(alert);

    // Auto remove after 5 seconds for success, 7 seconds for errors
    const autoRemoveTime = type === 'success' ? 5000 : 7000;
    const autoRemove = setTimeout(() => {
        alert.remove();
    }, autoRemoveTime);

    // Close button functionality
    const closeBtn = alert.querySelector('.alert-close');
    closeBtn.addEventListener('click', () => {
        clearTimeout(autoRemove);
        alert.remove();
    });
}

// 7. ATTACH EVENT LISTENERS TO FORMS
if (authLoginForm) {
    authLoginForm.addEventListener("submit", handleLogin);
    console.log("Attached login handler to main form");
}

if (modalLoginForm) {
    modalLoginForm.addEventListener("submit", handleModalLogin);
    console.log("Attached login handler to modal form");
}

if (registerForm) {
    registerForm.addEventListener("submit", handleRegister);
    console.log("Attached register handler to form");
}

    // // 6. REGISTER FUNCTIONALITY
    // function handleRegister(event) {
    //     event.preventDefault();
    //     console.log("Register form submitted");

    //     // Get form values
    //     const fullName = document.getElementById("hero-full-name").value.trim();
    //     const email = document.getElementById("hero-email").value.trim();
    //     const phone = document.getElementById("hero-phone").value.trim();
    //     const referralCode = document.getElementById("hero-code").value.trim();
    //     const password = document.getElementById("hero-password").value;
    //     const confirmPassword = document.getElementById("hero-confirm-password").value;

    //     // Get the submit button for loading state
    //     const submitButton = event.target.querySelector('button[type="submit"]');

    //     // Validate required fields
    //     if (!fullName || !email || !phone || !password || !confirmPassword) {
    //         alert("Please fill in all required fields.");
    //         return;
    //     }

    //     // Validate email format
    //     const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    //     if (!emailRegex.test(email)) {
    //         alert("Please enter a valid email address.");
    //         return;
    //     }

    //     // Validate phone (basic - at least 10 digits)
    //     const phoneRegex = /^[0-9]{10,15}$/;
    //     if (!phoneRegex.test(phone.replace(/\D/g, ''))) {
    //         alert("Please enter a valid phone number (10-15 digits).");
    //         return;
    //     }

    //     // Validate password match
    //     if (password !== confirmPassword) {
    //         alert("Passwords do not match. Please re-enter your password.");
    //         return;
    //     }

    //     // Validate password length
    //     if (password.length < 6) {
    //         alert("Password must be at least 6 characters long.");
    //         return;
    //     }

    //     // Show loading state on button
    //     if (submitButton) {
    //         submitButton.textContent = "Creating Account...";
    //         submitButton.disabled = true;
    //         submitButton.style.opacity = "0.7";
    //     }

    //     // Show loading page
    //     const loadingPage = document.getElementById("loadingPage");
    //     if (loadingPage) {
    //         loadingPage.style.display = "flex";
    //     }

    //     // Prepare registration data
    //     const registerData = {
    //         fullName: fullName,
    //         email: email,
    //         phone: phone,
    //         referralCode: referralCode || null,
    //         password: password
    //     };


    //     console.log("Sending registration request:", registerData);

    //     // Send POST request to /api/register
    //     fetch("/api/signup", {
    //         method: "POST",
    //         headers: {
    //             "Content-Type": "application/json"
    //         },
    //         body: JSON.stringify(registerData),
            
    //     })
    //     .then(response => {
    //         console.log("Registration response status:", response.status);
            
    //         if (!response.ok) {
    //             if (response.status === 400) {
    //                 throw new Error("Bad request - check your input data");
    //             } else if (response.status === 409) {
    //                 throw new Error("User already exists with this email or phone");
    //             } else {
    //                 throw new Error(`Server error: ${response.status}`);
    //             }
    //         }
    //         return response.json();
    //     })
    //     .then(data => {
    //         console.log("Registration successful, response data:", data);
            
    //         if (data.success) {
    //             alert("Registration successful! Welcome to Finicashi.");
                
                
    //             window.location.href = "/profile";
    //         } else {
    //             window.location.href = "/";
    //         }
    //     })
    //     .catch(error => {
    
    //         // Show appropriate error message
    //         if (error.message.includes("already exists")) {
    //             alert("An account with this email or phone already exists. Please login instead.");
    //         } else if (error.message.includes("Bad request")) {
    //             alert("Please check your information and try again.");
    //         }
            
    //         // Reset button state
    //         if (submitButton) {
    //             submitButton.textContent = "Create Account";
    //             submitButton.disabled = false;
    //             submitButton.style.opacity = "1";
    //         }
            
    //         // Hide loading page
    //         if (loadingPage) {
    //             loadingPage.style.display = "none";
    //         }
    //     });
    // }

    // // 7. ATTACH EVENT LISTENERS TO FORMS
    // if (authLoginForm) {
    //     authLoginForm.addEventListener("submit", handleLogin);
    //     console.log("Attached login handler to main form");
    // }

    // if (modalLoginForm) {
    //     modalLoginForm.addEventListener("submit", handleModalLogin);
    //     console.log("Attached login handler to modal form");
    // }

    // if (registerForm) {
    //     registerForm.addEventListener("submit", handleRegister);
    //     console.log("Attached register handler to form");
    // }

    // 8. BACKGROUND SLIDESHOW
    function initBackgroundSlideshow() {
        const slides = document.querySelectorAll('.background-slide');
        let currentSlide = 0;
        
        if (slides.length === 0) return;
        
        function showNextSlide() {
            slides[currentSlide].classList.remove('active');
            currentSlide = (currentSlide + 1) % slides.length;
            slides[currentSlide].classList.add('active');
        }
        
        // Change slide every 5 seconds
        setInterval(showNextSlide, 5000);
    }
    
    initBackgroundSlideshow();

    // 9. REFERRAL CODE AUTO-DETECT
    const params = new URLSearchParams(window.location.search);
    const referralCode = params.get("ref");
    if (referralCode) {
        const input = document.getElementById("hero-code");
        if (input) {
            input.value = referralCode.toUpperCase();
            console.log("Referral code auto-filled:", referralCode);
        }
    }

    console.log("Auth system initialization complete");
});