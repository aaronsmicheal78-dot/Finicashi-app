
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
        class HeroRegistration {
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
              // ---------------------------
// Registration Form JS
// ---------------------------

// Grab the form element
const registrationForm = document.getElementById('hero-registration-form');

// Attach submit handler
registrationForm.addEventListener('submit', handleRegistration);

// ==========================================================================
//
//    ..............REGISTRATION AND SIGNING UP................................
//=============================================================================
async function handleRegistration(event) {
    event.preventDefault();

    const formData = {
        fullName: document.getElementById('hero-full-name').value.trim(),
        email: document.getElementById('hero-email').value.trim(),
        phone: document.getElementById('hero-phone').value.trim(),
        password: document.getElementById('hero-password').value
    };

    // Validate input
    if (!validateForm(formData)) return;

    try {
        // Send POST request to Flask endpoint
        const response = await fetch('/api/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error(`Network response was not ok (${response.status})`);
        }

        const data = await response.json();

        if (data.success) {
            showMessage(data.message || 'Signup successful!', 'success');
            registrationForm.reset();
            // Redirect or load dashboard after delay
            setTimeout(() => {
                window.location.href = '/login'; // or dashboard
            }, 1500);
        } else {
            showMessage(data.message || 'Signup failed!', 'error');
        }

    } catch (error) {
        console.error('Error during signup:', error);
        showMessage('Something went wrong. Please try again.', 'error');
    }
}

// Simple input validation
function validateForm(f) {
    if (!f.fullName || !f.email || !f.phone || !f.password) {
        showMessage('Please fill in all fields', 'error');
        return false;
    }

    if (f.password.length < 6) {
        showMessage('Password must be at least 6 characters', 'error');
        return false;
    }

    return true;
}

// Display temporary messages
function showMessage(message, type) {
    const messageEl = document.createElement('div');
    messageEl.textContent = message;
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 18px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        ${type === 'success' ? 'background: #1dd1a1;' : 'background: #ff6b6b;'}
    `;
    document.body.appendChild(messageEl);
    setTimeout(() => messageEl.remove(), 3000);}

          

        // Initialize everything when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {
            new HeroBackground();
            new HeroRegistration();
        });

        // Add some interactive effects
        //document.addEventListener('mousemove', (e) => {
           // const heroSection = document.getElementById('hero-section');
          //  const xAxis = (window.innerWidth / 2 - e.pageX) / 25;
         //   const yAxis = (window.innerHeight / 2 - e.pageY) / 25;
            
        //    heroSection.style.transform = `rotateY(${xAxis}deg) rotateX(${yAxis}deg)`;
       // });

       

        // Close modal when clicking outside
        document.getElementById('loginModalOverlay').addEventListener('click', function(e) {
            if (e.target === this) {
                FincashProLogin.closeModal();
            }
        });

        // Close modal with Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                FincashProLogin.closeModal();
            }
        });

        console.log('Login modal script loaded. Use FincashProLogin.openModal() to open the modal.');

 
                