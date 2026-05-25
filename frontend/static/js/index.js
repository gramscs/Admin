// Contact form handling with toast notifications and local storage
document.addEventListener('DOMContentLoaded', function() {
    console.log('Contact form script loaded');
    
    const contactForm = document.getElementById('contactForm');
    
    if (contactForm) {
        console.log('Contact form found');
        
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent default form submission
            console.log('Form submitted');
            
            // Get form data
            const formData = new FormData(contactForm);
            const formObject = {};
            formData.forEach((value, key) => {
                formObject[key] = value;
            });
            
            // Add timestamp
            formObject.timestamp = new Date().toISOString();
            
            console.log('Form data:', formObject);
            
            // Validate form
            if (!validateContactForm(formObject)) {
                showToast('Please fill in all required fields correctly.', 'error');
                return;
            }
            
            // Show loading state
            const submitButton = contactForm.querySelector('button[type="submit"]');
            const originalText = submitButton.querySelector('.btn-text').textContent;
            submitButton.querySelector('.btn-text').textContent = 'Sending...';
            submitButton.disabled = true;
            
            // Save to localStorage
            saveContactSubmission(formObject);
            
            // Submit to server (optional - for backend processing)
            fetch('/contact', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                // backend returns HTML; treat any 2xx as success
                if (response.ok) {
                    showToast('Thank you! Your message has been received.', 'success');
                    contactForm.reset();
                } else {
                    showToast('Saved locally — server unavailable.', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Saved locally — server unavailable.', 'error');
                contactForm.reset();
            })
            .finally(() => {
                // Reset button state
                submitButton.querySelector('.btn-text').textContent = originalText;
                submitButton.disabled = false;
            });
        });
    } else {
        console.error('Contact form not found');
    }
});

// Form validation function
function validateContactForm(formData) {
    const required = ['name', 'email', 'phone', 'subject', 'message'];
    
    for (let field of required) {
        if (!formData[field] || formData[field].trim().length === 0) {
            console.log('Validation failed for field:', field);
            return false;
        }
    }
    
    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
        console.log('Email validation failed');
        return false;
    }
    
    // Phone validation - make it more lenient
    const phoneRegex = /[\d+\-() ]{7,20}/;
    if (!phoneRegex.test(formData.phone)) {
        console.log('Phone validation failed');
        return false;
    }
    
    console.log('Validation passed');
    return true;
}

// Save contact submission to localStorage
function saveContactSubmission(formData) {
    try {
        let submissions = JSON.parse(localStorage.getItem('contactSubmissions')) || [];
        submissions.push(formData);
        
        // Keep only last 50 submissions to prevent storage overflow
        if (submissions.length > 50) {
            submissions = submissions.slice(-50);
        }
        
        localStorage.setItem('contactSubmissions', JSON.stringify(submissions));
        console.log('Saved to localStorage. Total submissions:', submissions.length);
    } catch (error) {
        console.error('Error saving to localStorage:', error);
    }
}

// Toast notification system
function showToast(message, type = 'info') {
    console.log('Showing toast:', message, type);
    
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast-notification');
    existingToasts.forEach(toast => toast.remove());
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <div class="toast-icon">
                ${type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ'}
            </div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => toast.classList.add('toast-show'), 100);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.remove('toast-show');
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
}

// Debug function to check stored submissions
function viewStoredSubmissions() {
    const submissions = JSON.parse(localStorage.getItem('contactSubmissions')) || [];
    console.table(submissions);
    return submissions;
}

// Make debug function available globally
window.viewStoredSubmissions = viewStoredSubmissions;