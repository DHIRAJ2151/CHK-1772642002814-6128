

// Mobile Menu Toggle (guarded)
const menuToggle = document.getElementById('mobile-menu');
const navLinks = document.getElementById('nav-links');

if (menuToggle && navLinks) {
    menuToggle.addEventListener('click', () => {
        navLinks.classList.toggle('active');
    });
}

// Page Navigation
function showPage(pageId) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show selected page
    document.getElementById(`${pageId}-page`).classList.add('active');
    
    // Close mobile menu if open
    if (navLinks) navLinks.classList.remove('active');
    
    // Scroll to top
    window.scrollTo(0, 0);
}

// Disease Detection Image Upload (guarded for pages without these elements)
const uploadArea = document.getElementById('uploadArea');
const imageUpload = document.getElementById('imageUpload');
const imagePreview = document.getElementById('imagePreview');
const analyzeBtn = document.getElementById('analyzeBtn');
const selectAnotherBtn = document.getElementById('selectAnotherBtn');
const detectionResults = document.getElementById('detectionResults');
const shareDiseaseBtn = document.getElementById('shareDiseaseBtn');
const detectionResultsBody = document.getElementById('detectionResultsBody');

let lastDiseaseShareText = '';

if (uploadArea && imageUpload) {
    uploadArea.addEventListener('click', () => {
        imageUpload.click();
    });
}

if (imageUpload && imagePreview && uploadArea && analyzeBtn) {
    imageUpload.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(event) {
                imagePreview.src = event.target.result;
                imagePreview.style.display = 'block';
                analyzeBtn.style.display = 'inline-block';
                if (selectAnotherBtn) selectAnotherBtn.style.display = 'inline-block';

                const icon = uploadArea.querySelector('.upload-icon');
                if (icon) icon.style.display = 'none';

                const ps = uploadArea.querySelectorAll('p');
                if (ps && ps.length) {
                    ps.forEach((el, idx) => {
                        if (idx !== 0) el.style.display = 'none';
                    });
                    ps[0].textContent = file.name;
                }
            }
            reader.readAsDataURL(file);
        }
    });
}

if (selectAnotherBtn && imageUpload) {
    selectAnotherBtn.addEventListener('click', function() {
        imageUpload.value = '';
        imageUpload.click();
    });
}

if (shareDiseaseBtn) {
    shareDiseaseBtn.addEventListener('click', async function() {
        if (!lastDiseaseShareText) return;

        const encoded = encodeURIComponent(lastDiseaseShareText);
        const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || '');

        // Open WhatsApp explicitly (so WhatsApp is always offered)
        const waUrl = isMobile
            ? `https://wa.me/?text=${encoded}`
            : `https://web.whatsapp.com/send?text=${encoded}`;
        try { window.open(waUrl, '_blank', 'noopener'); } catch (e) {}

        // Also try native share (some mobiles show WhatsApp in share sheet)
        try {
            if (navigator.share) {
                await navigator.share({
                    title: 'Krushi - Disease Detection Result',
                    text: lastDiseaseShareText,
                });
            }
        } catch (e) {}

        // Clipboard fallback so user can paste anywhere
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(lastDiseaseShareText);
            }
        } catch (e) {}
    });
}

if (analyzeBtn && imageUpload && detectionResults) analyzeBtn.addEventListener('click', async function() {
    if (!imageUpload.files || !imageUpload.files[0]) {
        alert('Please choose an image first.');
        return;
    }
    const resultsTarget = detectionResultsBody || detectionResults;
    resultsTarget.innerHTML = '<p>Analyzing image for better results... Please wait.</p>';
    lastDiseaseShareText = '';
    if (shareDiseaseBtn) shareDiseaseBtn.style.display = 'none';

    try {
        const formData = new FormData();
        formData.append('image', imageUpload.files[0]);

        const resp = await fetch('/api/analyze-disease/', {
            method: 'POST',
            body: formData
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${resp.status}`);
        }

        const data = await resp.json();

        const toPercent = (v) => {
            if (typeof v === 'number') return `${Math.round(v * 100)}%`;
            if (typeof v === 'string' && v.includes('%')) return v;
            const n = Number(v);
            return isNaN(n) ? '—' : `${Math.round(n * 100)}%`;
        };

        const asTextList = (value) => {
            if (value == null) return [];
            if (Array.isArray(value)) {
                return value.map(x => (x == null ? '' : String(x).trim())).filter(Boolean);
            }
            if (typeof value === 'string') {
                const raw = value.trim();
                if (!raw) return [];
                // Split common formats:
                // - newline-separated
                // - bullet-separated (•)
                // - sentence blocks (e.g., "... . Next ...")
                let parts = raw.split(/\r?\n+/).map(s => s.trim()).filter(Boolean);
                if (parts.length <= 1) {
                    parts = raw.split(/[•\u2022]+/).map(s => s.trim()).filter(Boolean);
                }
                if (parts.length <= 1) {
                    parts = raw.split(/\s*;\s*/).map(s => s.trim()).filter(Boolean);
                }
                if (parts.length <= 1) {
                    // Heuristic: split on ". " when next chunk looks like a new instruction
                    parts = raw.split(/\.\s+(?=[A-Z0-9])/).map(s => s.trim()).filter(Boolean);
                    // Re-add trailing period for readability
                    parts = parts.map(p => (p.endsWith('.') ? p : `${p}.`));
                }
                return parts;
            }
            return [String(value).trim()].filter(Boolean);
        };

        const escapeHtml = (s) => String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');

        const section = (title, innerHtml) => (
            `<div class="disease-result"><h4>${escapeHtml(title)}</h4>${innerHtml}</div>`
        );

        const ul = (items) => {
            const safe = asTextList(items).map(i => `<li>${escapeHtml(i)}</li>`).join('');
            return safe ? `<ul>${safe}</ul>` : '';
        };

        const ol = (items) => {
            const safe = asTextList(items).map(i => `<li>${escapeHtml(i)}</li>`).join('');
            return safe ? `<ol>${safe}</ol>` : '';
        };

        let html = '';
        const shareLines = [];

        if (data.species) {
            html += section('Identified Species', `<ul><li>${escapeHtml(data.species)}</li></ul>`);
            shareLines.push('Identified Species:');
            shareLines.push(`- ${String(data.species).trim()}`);
            shareLines.push('');
        }

        if (data.health_status) {
            html += section('Health Status', `<ul><li>${escapeHtml(data.health_status)}</li></ul>`);
            shareLines.push('Health Status:');
            shareLines.push(`- ${String(data.health_status).trim()}`);
            shareLines.push('');
        }

        const diseases = Array.isArray(data.detected_diseases) ? data.detected_diseases : [];
        if (diseases.length) {
            const items = diseases.map((d, idx) => {
                const name = d?.name || 'Unknown';
                const conf = toPercent(d?.confidence);
                const blocks = [];
                if (d?.description) {
                    blocks.push(`<ul><li><strong>Description:</strong> ${escapeHtml(String(d.description).trim())}</li></ul>`);
                }
                const recs = asTextList(d?.recommended_treatments);
                if (recs.length) {
                    blocks.push(`<div><strong>Treatments:</strong>${ul(recs)}</div>`);
                }
                return `<li><strong>${escapeHtml(`${idx + 1}. ${name}`)}</strong> (${escapeHtml(conf)} confidence)${blocks.length ? `<div style="margin-top:8px;">${blocks.join('')}</div>` : ''}</li>`;
            }).join('');
            html += section('Detected Diseases', items ? `<ol>${items}</ol>` : '<p>No diseases detected.</p>');

            shareLines.push('Detected Diseases:');
            diseases.forEach((d, idx) => {
                const name = d?.name || 'Unknown';
                const conf = toPercent(d?.confidence);
                shareLines.push(`${idx + 1}. ${name} (${conf})`);
                if (d?.description) shareLines.push(`   - Description: ${String(d.description).trim()}`);
                const recs = asTextList(d?.recommended_treatments);
                if (recs.length) shareLines.push(`   - Treatments: ${recs.join('; ')}`);
            });
            shareLines.push('');
        }

        const pests = Array.isArray(data.pests) ? data.pests : [];
        if (pests.length) {
            const items = pests.map((p, idx) => {
                const name = p?.name || 'Unknown';
                const conf = toPercent(p?.confidence);
                const ctrl = asTextList(p?.control);
                const blocks = [];
                if (ctrl.length) {
                    blocks.push(`<div><strong>Control:</strong>${ul(ctrl)}</div>`);
                }
                return `<li><strong>${escapeHtml(`${idx + 1}. ${name}`)}</strong> (${escapeHtml(conf)} confidence)${blocks.length ? `<div style="margin-top:8px;">${blocks.join('')}</div>` : ''}</li>`;
            }).join('');
            html += section('Detected Pests', items ? `<ol>${items}</ol>` : '<p>No pests detected.</p>');

            shareLines.push('Detected Pests:');
            pests.forEach((p, idx) => {
                const name = p?.name || 'Unknown';
                const conf = toPercent(p?.confidence);
                shareLines.push(`${idx + 1}. ${name} (${conf})`);
                const ctrl = asTextList(p?.control);
                if (ctrl.length) shareLines.push(`   - Control: ${ctrl.join('; ')}`);
            });
            shareLines.push('');
        }

        const tips = asTextList(data.care_tips);
        if (tips.length) {
            html += section('Care Tips', ol(tips));
            shareLines.push('Care Tips:');
            tips.forEach(t => shareLines.push(`- ${t}`));
            shareLines.push('');
        }

        const ferts = asTextList(data.fertilizer_recommendations);
        if (ferts.length) {
            html += section('Fertilizer Recommendations', ol(ferts));
            shareLines.push('Fertilizer Recommendations:');
            ferts.forEach(f => shareLines.push(`- ${f}`));
            shareLines.push('');
        }

        if (!html) {
            html = '<p>No clear findings. Try another image with good lighting and focus.</p>';
            shareLines.push('No clear findings. Try another image with good lighting and focus.');
        }

        resultsTarget.innerHTML = html;
        lastDiseaseShareText = shareLines.join('\n').trim();
        if (shareDiseaseBtn && lastDiseaseShareText) shareDiseaseBtn.style.display = 'inline-block';
    } catch (err) {
        const resultsTarget = detectionResultsBody || detectionResults;
        resultsTarget.innerHTML = `<p style="color:red;">Analysis failed: ${err.message}</p>`;
        lastDiseaseShareText = '';
        if (shareDiseaseBtn) shareDiseaseBtn.style.display = 'none';
    }
});

// Helper function to get cookie value by name
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Soil Analysis Form (crop only)
const soilForm = document.getElementById('soilForm');
const soilResults = document.getElementById('soilResults');
const recommendedCrop = document.getElementById('recommendedCrop');
const soilHealthStatus = document.getElementById('soilHealthStatus');
const fertilizerRecommendations = document.getElementById('fertilizerRecommendations');
const improvementSuggestions = document.getElementById('improvementSuggestions');
const topRecommendations = document.getElementById('topRecommendations');

// OCR: PDF extraction for soil metrics
const ocrBtn = document.getElementById('ocrExtractBtn');
const ocrFile = document.getElementById('soilPdf');
const ocrStatus = document.getElementById('ocrStatus');

if (ocrBtn && ocrFile) {
    ocrBtn.addEventListener('click', async () => {
        if (!ocrFile.files || !ocrFile.files[0]) {
            if (ocrStatus) ocrStatus.innerHTML = '<span style="color:var(--warning-color, #b07600);">Please choose a PDF file first.</span>';
            return;
        }

        const file = ocrFile.files[0];
        if (!/\.pdf$/i.test(file.name)) {
            if (ocrStatus) ocrStatus.innerHTML = '<span style="color:var(--danger-color, #c62828);">Only PDF files are supported.</span>';
            return;
        }

        if (ocrStatus) ocrStatus.innerHTML = '<span>Extracting values from PDF... Please wait.</span>';

        try {
            const fd = new FormData();
            fd.append('file', file);
            const resp = await fetch('/api/ocr-extract-soil/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken') || ''
                },
                body: fd
            });
            const data = await resp.json().catch(() => ({ error: 'Invalid response from server.' }));
            if (!resp.ok || data.error) {
                const msg = data.error || `Request failed (HTTP ${resp.status})`;
                if (ocrStatus) ocrStatus.innerHTML = `<span style="color:var(--danger-color, #c62828);">${msg}</span>`;
                return;
            }

            // Helper to set value if present
            const setVal = (id, val) => {
                if (val == null || val === '') return;
                const el = document.getElementById(id);
                if (!el) return;
                const num = parseFloat(String(val).replace(/,/g, ''));
                if (!isNaN(num)) el.value = num;
            };

            setVal('nitrogen', data.n);
            setVal('phosphorus', data.p);
            setVal('potassium', data.k);
            setVal('phLevel', data.ph);
            setVal('temperature', data.temperature);
            setVal('humidity', data.humidity);
            setVal('rainfall', data.rainfall);

            if (ocrStatus) ocrStatus.innerHTML = '<span style="color:var(--success-color, #2e7d32);">Extraction complete. Fields auto-filled where found.</span>';
        } catch (e) {
            if (ocrStatus) ocrStatus.innerHTML = `<span style="color:var(--danger-color, #c62828);">Extraction failed: ${e.message || e}</span>`;
        }
    });
}

if (soilForm) soilForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    // Helper function to safely parse float values
    const getFloatValue = (id) => {
        const element = document.getElementById(id);
        if (!element) return null;
        const value = element.value.trim();
        if (value === '') return null;
        const num = parseFloat(value);
        return isNaN(num) ? null : num;
    };

    // Collect inputs with validation
    const phLevel = getFloatValue('phLevel');
    const nitrogen = getFloatValue('nitrogen');
    const phosphorus = getFloatValue('phosphorus');
    const potassium = getFloatValue('potassium');
    const temperature = getFloatValue('temperature');
    const humidity = getFloatValue('humidity');
    const rainfall = getFloatValue('rainfall');

    // Validate required fields
    const missingFields = [];
    if (phLevel === null) missingFields.push('pH Level');
    if (nitrogen === null) missingFields.push('Nitrogen');
    if (phosphorus === null) missingFields.push('Phosphorus');
    if (potassium === null) missingFields.push('Potassium');
    if (temperature === null) missingFields.push('Temperature');
    if (humidity === null) missingFields.push('Humidity');
    if (rainfall === null) missingFields.push('Rainfall');

    if (missingFields.length > 0) {
        alert(`Please fill in all required fields:\n\n${missingFields.join('\n')}`);
        return;
    }

    const payload = {
        ph_level: phLevel,
        nitrogen: nitrogen,
        phosphorus: phosphorus,
        potassium: potassium,
        temperature: temperature,
        humidity: humidity,
        rainfall: rainfall
    };

    // Show loading state
    soilResults.style.display = 'block';
    if (soilHealthStatus) soilHealthStatus.innerHTML = '';
    if (fertilizerRecommendations) fertilizerRecommendations.innerHTML = '';
    if (improvementSuggestions) improvementSuggestions.innerHTML = '';
    if (topRecommendations) topRecommendations.innerHTML = '';
    if (recommendedCrop) {
        recommendedCrop.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Analyzing soil data and predicting the best crop...</p>
            </div>
        `;
    }

    try {
        console.log('Sending payload:', payload);
        const resp = await fetch('/api/analyze-soil/', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || ''
            },
            body: JSON.stringify(payload)
        });

        const responseData = await resp.json();
        console.log('Received response:', responseData);

        if (!resp.ok) {
            throw new Error(responseData.error || responseData.prediction_error || `HTTP ${resp.status}`);
        }

        if (recommendedCrop) {
            if (responseData.recommended_crop) {
                const cropName = responseData.recommended_crop.charAt(0).toUpperCase() + responseData.recommended_crop.slice(1);
                recommendedCrop.innerHTML = `
                    <div class="result-success">
                
                        <div class="crop-result">
                            <i class="fas fa-seedling"></i>
                            <span>${cropName}</span>
                        </div>
                    </div>
                `;
                if (Array.isArray(responseData.top_recommendations) && topRecommendations) {
                    const items = responseData.top_recommendations.map((r, idx) => {
                        const name = (r.crop || '').toString();
                        const score = typeof r.score === 'number' ? `${Math.round(r.score * 100)}%` : '';
                        return `<li>${idx + 1}. ${name}${score ? ` — <strong>${score}</strong>` : ''}</li>`;
                    }).join('');
                    topRecommendations.innerHTML = items || '<li>No additional recommendations</li>';
                }
            } else if (responseData.prediction_error) {
                recommendedCrop.innerHTML = `
                    <div class="result-error">
                        <h4>Analysis Issue</h4>
                        <p>${responseData.prediction_error}</p>
                    </div>
                `;
            } else {
                recommendedCrop.innerHTML = `
                    <div class="result-warning">
                        <h4>No Prediction Available</h4>
                        <p>We couldn't determine a crop recommendation. Please check your input values and try again.</p>
                    </div>
                `;
            }
        }
    } catch (err) {
        console.error('Prediction error:', err);
        if (recommendedCrop) {
            recommendedCrop.innerHTML = `
                <div class="result-error">
                    <h4>Prediction Failed</h4>
                    <p>${err.message || 'An unexpected error occurred. Please try again later.'}</p>
                </div>
            `;
        }
    }
});

// Form submission handlers
const loginForm = document.getElementById('login-form');
if (loginForm) loginForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    // Here you would typically send data to server
    alert(`Login attempt with email: ${email}\nPassword: ${password}\n\nThis would be sent to server in a real application`);
    
    // For demo purposes, just show a success message
    alert('Login successful! Redirecting to home page...');
    showPage('home');
});

const registerForm = document.getElementById('register-form');
if (registerForm) registerForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const name = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const phone = document.getElementById('register-phone').value;
    const password = document.getElementById('register-password').value;
    
    // Validate password match
    if (password !== document.getElementById('register-confirm').value) {
        alert('Passwords do not match!');
        return;
    }
    
    // Here you would typically send data to server
    alert(`Registration submitted:\nName: ${name}\nEmail: ${email}\nPhone: ${phone}\nPassword: ${password}\n\nThis would be sent to server in a real application`);
    
    // For demo purposes, just show a success message
    alert('Registration successful! Please login with your credentials.');
    showPage('login');
});

// Contact form submission
const contactForm = document.getElementById('contactForm');
if (contactForm) contactForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const subject = document.getElementById('subject').value;
    const message = document.getElementById('message').value;
    
    // Here you would typically send data to server
    alert(`Message sent:\nName: ${name}\nEmail: ${email}\nSubject: ${subject}\nMessage: ${message}\n\nThis would be sent to server in a real application`);
    
    // For demo purposes, just show a success message
    alert('Thank you for your message! We will get back to you soon.');
    this.reset();
});

// Contact form submission (contact page)
const contactFormPage = document.getElementById('contactFormPage');
if (contactFormPage) contactFormPage.addEventListener('submit', function(e) {
    e.preventDefault();
    const name = document.getElementById('contact-name').value;
    const email = document.getElementById('contact-email').value;
    const subject = document.getElementById('contact-subject').value;
    const message = document.getElementById('contact-message').value;
    
    // Here you would typically send data to server
    alert(`Message sent:\nName: ${name}\nEmail: ${email}\nSubject: ${subject}\nMessage: ${message}\n\nThis would be sent to server in a real application`);
    
    // For demo purposes, just show a success message
    alert('Thank you for your message! We will get back to you soon.');
    this.reset();
});

// Rating form submission
const ratingForm = document.getElementById('ratingForm');
if (ratingForm) ratingForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const rating = document.querySelector('input[name="rating"]:checked')?.value;
    const name = document.getElementById('rating-name').value;
    const comment = document.getElementById('rating-comment').value;
    
    if (!rating) {
        alert('Please select a rating!');
        return;
    }
    
    // Here you would typically send data to server
    alert(`Rating submitted:\nRating: ${rating} stars\nName: ${name}\nComment: ${comment}\n\nThis would be sent to server in a real application`);
    
    // For demo purposes, just show a success message
    alert('Thank you for your feedback! We appreciate your time.');
    this.reset();
    showPage('home');
});

// Rating stars: enforce left-to-right selection/fill
const ratingStars = document.querySelector('.rating-stars');
if (ratingStars) {
    const labels = Array.from(ratingStars.querySelectorAll('label'));
    const inputs = Array.from(ratingStars.querySelectorAll('input[name="rating"]'));

    function applyFill(val) {
        const n = parseInt(val, 10);
        labels.forEach(l => {
            const forAttr = l.getAttribute('for') || '';
            const num = parseInt(forAttr.replace('star', ''), 10);
            if (!isNaN(num)) {
                l.classList.toggle('filled', num <= n);
            }
        });
    }

    // Initialize based on any pre-checked input
    const checked = inputs.find(i => i.checked);
    if (checked) applyFill(checked.value);

    // Update active class on change
    inputs.forEach(input => {
        input.addEventListener('change', () => applyFill(input.value));
    });

    // Optional: visual preview on hover without changing selection
    labels.forEach(label => {
        label.addEventListener('mouseenter', () => {
            const forAttr = label.getAttribute('for') || '';
            const num = parseInt(forAttr.replace('star', ''), 10);
            if (!isNaN(num)) applyFill(num);
        });
    });
    ratingStars.addEventListener('mouseleave', () => {
        const current = inputs.find(i => i.checked);
        if (current) applyFill(current.value); else labels.forEach(l => l.classList.remove('filled'));
    });
}

// Newsletter subscription (real backend)
const newsletterForm = document.getElementById('newsletterForm');
if (newsletterForm) newsletterForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const emailInput = this.querySelector('input[type="email"]');
    const email = (emailInput && emailInput.value || '').trim();
    if (!email) {
        alert('Please enter your email.');
        return;
    }
    try {
        const resp = await fetch('/api/newsletter/subscribe/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-CSRFToken': (window.getCSRFToken ? window.getCSRFToken() : ''),
            },
            credentials: 'same-origin',
            body: new URLSearchParams({ email }),
        });
        const data = await resp.json().catch(() => ({ success: false, message: 'Invalid server response' }));
        if (!resp.ok || !data.success) {
            throw new Error(data.message || `Request failed (${resp.status})`);
        }
        alert(data.message || 'Subscribed successfully!');
        this.reset();
    } catch (err) {
        alert(`Subscription failed: ${err.message || err}`);
    }
});

// Filter buttons in shop
const filterBtns = document.querySelectorAll('.filter-btn');
filterBtns.forEach(btn => {
    btn.addEventListener('click', function() {
        filterBtns.forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        
        // Get the filter category
        const category = this.textContent.toLowerCase();
        
        // Filter products (in a real app, this would be done server-side)
        const products = document.querySelectorAll('.product-card');
        products.forEach(product => {
            if (category === 'all') {
                product.style.display = 'block';
            } else {
                const productCategory = product.querySelector('.product-category').textContent.toLowerCase();
                if (productCategory.includes(category)) {
                    product.style.display = 'block';
                } else {
                    product.style.display = 'none';
                }
            }
        });
    });
});

// Track login state
let isLoggedIn = false;

// Add to cart functionality
const addToCartBtns = document.querySelectorAll('.add-to-cart');
addToCartBtns.forEach(btn => {
    btn.addEventListener('click', function() {

        
        const product = this.closest('.product-card');
        const title = product.querySelector('.product-title').textContent;
        const price = product.querySelector('.product-price').textContent;
        
        alert(`${title} (${price}) added to cart!\n\nIn a real application, this would update the shopping cart.`);
    });
});

// Animation on scroll
window.addEventListener('scroll', function() {
    const elements = document.querySelectorAll('.feature-card, .product-card');
    elements.forEach(el => {
        const position = el.getBoundingClientRect().top;
        const windowHeight = window.innerHeight;
        
        if (position < windowHeight - 100) {
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }
    });
});

// Initialize chatbot with welcome message (only if chat widget is present)
setTimeout(() => {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    const messageElement = document.createElement('div');
    messageElement.className = 'message bot-message';
    messageElement.innerHTML = "Hello! I'm Krushi Assistant. I can help you with soil analysis recommendations, crop disease information, and product suggestions. How can I help you today?";
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}, 1000);