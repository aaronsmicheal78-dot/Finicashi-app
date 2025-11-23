
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


// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new HeroBackground();
});

        // Registration Form Handler
        class HeeroRegistration {
            constructor() {
                this.init();
            }

            init() {
                this.initializeEventListeners();
            }

            initializeEventListeners() {
                const form = document.getElementById('hero-registration-form');
                form.addEventListener('submit', (e) => this.handleRegistration(e));

                // CTA buttons
                document.getElementById('hero-watch-demo').addEventListener('click', () => {
                    this.showDemoModal();
                });

                document.getElementById('hero-learn-more').addEventListener('click', () => {
                    this.scrollToFeatures();
                });
            }}

 
document.getElementById('hero-registration-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    console.log('🔵 FORM SUBMISSION STARTED');
    
    const btn = this.querySelector('button[type="submit"]');
    const messageBox = document.getElementById('registration-message');
    
    console.log('Button element:', btn);
    console.log('Message box element:', messageBox);
    
    // Test 1: Immediate button text change
    btn.textContent = 'Creating Account...';
    btn.disabled = true;
    console.log('Button text changed to:', btn.textContent);
    
    // Test 2: Immediate message display
    if (messageBox) {
        messageBox.textContent = 'Processing your registration...';
        messageBox.style.display = 'block';
        messageBox.style.backgroundColor = '#e7f3ff';
        messageBox.style.color = '#004085';
        messageBox.style.padding = '10px';
        messageBox.style.borderRadius = '4px';
        messageBox.style.margin = '10px 0';
        console.log('Message box updated');
    }
    
    try {
        console.log('🟡 Making API request...');
        
        const formData = {
            fullName: document.getElementById('hero-full-name').value,
            email: document.getElementById('hero-email').value,
            phone: document.getElementById('hero-phone').value,
            password: document.getElementById('hero-password').value,
            referralCode: document.getElementById('hero-code').value.trim(),
        };
        
        const response = await fetch('/api/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        console.log('🟢 API Response:', data);
        console.log('Response status:', response.status);

        if (!response.ok) {
            throw new Error(data.error || `Signup failed with status ${response.status}`);
        }

        alert('✅ Registration Successful! Your account has been created.');
        
        this.reset();

        // Redirect
        setTimeout(() => {
            window.location.href = '/';
        }, 2000);

    } catch (error) {
        console.error('🔴 ERROR:', error);
        
        // ERROR
        btn.textContent = 'Sign Up';
        btn.disabled = false;
        btn.style.backgroundColor = ''; // Reset background
        
        if (messageBox) {
            messageBox.textContent = error.message || 'Registration failed. Please try again.';
            messageBox.style.backgroundColor = '#f8d7da';
            messageBox.style.color = '#721c24';
            messageBox.style.border = '1px solid #f5c6cb';
        }
        
        // Also show alert as fallback
        alert('Error: ' + (error.message || 'Registration failed'));
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const urlParams = new URLSearchParams(window.location.search);
    const ref = urlParams.get("ref");

    if (ref) {
        document.getElementById("hero-code").value = ref;
    }
});


    
new HeroRegistration();
// toggle login password
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const toggleButton = document.querySelector('.password-toggle i');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleButton.className = 'fas fa-eye-slash';
    } else {
        passwordInput.type = 'password';
        toggleButton.className = 'fas fa-eye';
    }
}                
// RESET PASSWORD//

class PasswordReset {
    constructor() {
        this.initEventListeners();
    }

    initEventListeners() {
        // Request reset code
        document.getElementById('request-reset-btn').addEventListener('click', () => {
            this.requestResetCode();
        });

        // Reset password
        document.getElementById('reset-password-btn').addEventListener('click', () => {
            this.resetPassword();
        });

        // Enter key support
        document.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                if (!document.getElementById('reset-password-form').classList.contains('hidden')) {
                    this.resetPassword();
                } else {
                    this.requestResetCode();
                }
            }
        });
    }

    async requestResetCode() {
        const phone = document.getElementById('phone').value.trim();
        const email = document.getElementById('email').value.trim();
        const messageDiv = document.getElementById('request-message');

        // Basic validation
        if (!phone || !email) {
            this.showMessage(messageDiv, 'Please fill in all fields', 'error');
            return;
        }

        // Uganda phone validation
        const phoneRegex = /^\+2567\d{8}$/;
        if (!phoneRegex.test(phone)) {
            this.showMessage(messageDiv, 'Please enter a valid Uganda phone number (+2567XXXXXXXX)', 'error');
            return;
        }

        // Email validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            this.showMessage(messageDiv, 'Please enter a valid email address', 'error');
            return;
        }

        try {
            this.showMessage(messageDiv, 'Sending reset code...', 'info');
            
            const response = await fetch('/password/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phone: phone,
                    email: email
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.showMessage(messageDiv, data.message, 'success');
                // Switch to reset password form
                document.getElementById('request-reset-form').classList.add('hidden');
                document.getElementById('reset-password-form').classList.remove('hidden');
            } else {
                this.showMessage(messageDiv, data.error || 'Failed to send reset code', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showMessage(messageDiv, 'Network error. Please try again.', 'error');
        }
    }

    async resetPassword() {
        const phone = document.getElementById('phone').value.trim();
        const email = document.getElementById('email').value.trim();
        const resetCode = document.getElementById('reset-code').value.trim();
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        const messageDiv = document.getElementById('reset-message');

        // Validation
        if (!resetCode || !newPassword || !confirmPassword) {
            this.showMessage(messageDiv, 'Please fill in all fields', 'error');
            return;
        }

        if (newPassword !== confirmPassword) {
            this.showMessage(messageDiv, 'Passwords do not match', 'error');
            return;
        }

        if (newPassword.length < 6) {
            this.showMessage(messageDiv, 'Password must be at least 6 characters', 'error');
            return;
        }

        try {
            this.showMessage(messageDiv, 'Resetting password...', 'info');

            const response = await fetch('/password/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phone: phone,
                    email: email,
                    reset_code: resetCode,
                    new_password: newPassword
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.showMessage(messageDiv, data.message, 'success');
                // Redirect to login after successful reset
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            } else {
                this.showMessage(messageDiv, data.error || 'Password reset failed', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showMessage(messageDiv, 'Network error. Please try again.', 'error');
        }
    }

    showMessage(element, message, type) {
        element.textContent = message;
        element.className = type + '-message';
        element.classList.remove('hidden');
        
        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                element.classList.add('hidden');
            }, 5000);
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new PasswordReset();
});