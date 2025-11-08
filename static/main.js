
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
                // Set background images
                this.slides.forEach((slide, index) => {
                    slide.style.backgroundImage = `url(${backgroundImages[index]})`;
                });

                // Start slideshow
                this.startSlideshow();
            }

            startSlideshow() {
                setInterval(() => {
                    this.nextSlide();
                }, 5000); // Change slide every 5 seconds
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

 

  class HeroRegistration {
    constructor() {
        this.handleRegistration = this.handleRegistration.bind(this);
        this.init();
    }

    init() {
        document.addEventListener('DOMContentLoaded', () => {
            const registrationForm = document.getElementById('hero-registration-form');
            if (registrationForm) {
                registrationForm.addEventListener('submit', this.handleRegistration);
            }
        });
    }

    async handleRegistration(event) {
        event.preventDefault();
        const registrationForm = event.target;
        
        // Show loading state
        this.setLoadingState(true);

        const formData = {
            fullName: document.getElementById('hero-full-name').value.trim(),
            email: document.getElementById('hero-email').value.trim().toLowerCase(),
            phone: document.getElementById('hero-phone').value.trim(),
            password: document.getElementById('hero-password').value
        };

        // Enhanced validation
        if (!this.validateForm(formData)) {
            this.setLoadingState(false);
            return;
        }

        try {
            const response = await fetch('/api/signup', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `Signup failed with status ${response.status}`);
            }

            this.showMessage(data.message || 'Signup successful!', 'success');
            registrationForm.reset();

            // Redirect after success
            setTimeout(() => { 
                window.location.href = '/'; 
            }, 1500);

        } catch (error) {
            console.error('Signup error:', error);
            this.showMessage(
                error.message || 'Network error. Please try again.', 
                'error'
            );
        } finally {
            this.setLoadingState(false);
        }
    }

    validateForm(f) {
        if (!f.fullName || !f.email || !f.phone || !f.password) {
            this.showMessage('Please fill in all fields', 'error');
            return false;
        }
        
        if (f.password.length < 6) {
            this.showMessage('Password must be at least 6 characters', 'error');
            return false;
        }
        
        if (!this.isValidEmail(f.email)) {
            this.showMessage('Please enter a valid email address', 'error');
            return false;
        }
        
        return true;
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    setLoadingState(isLoading) {
        const submitBtn = document.querySelector('#hero-registration-form button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = isLoading;
            submitBtn.textContent = isLoading ? 'Creating Account...' : 'Sign Up';
        }
    }

    showMessage(msg, type) {
        const msgBox = document.getElementById('registration-message');
        if (!msgBox) return;

        msgBox.textContent = msg;
        msgBox.className = `message ${type}`;
        msgBox.style.display = 'block';

        setTimeout(() => {
            msgBox.textContent = '';
            msgBox.className = '';
            msgBox.style.display = 'none';
        }, 5000);
    }
}

new HeroRegistration();

                