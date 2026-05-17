/* 
 * Cinema Focus - Core SPA Application Controller
 * Handles client-side routing, live catalog rendering, quick view modals, 
 * local storage persistent enquiry cart, and quotation requests.
 */

// --- Global Application States ---
let currentTab = 'home';
let cartItems = []; // List of product IDs
let activeCategory = 'all';
let activeBrand = 'all';
let searchQuery = '';
let currentSort = 'default';

// --- Hardcoded National Dealers Database (Extracted from WordPress DB) ---
const dealersData = {
    "chennai": [
        {
            "name": "Cinema Focus (India) Corporate HQ",
            "contact": "Mr. Vijay Kumar",
            "phone": "+91 98410 35821",
            "landline": "044 2811 7722",
            "address": "New Decor Towers, No.71 Dr.Radhakrishnan Salai, Mylapore, Chennai - 600004",
            "brands": "Kii Audio, ProAc, Audiovector, System Audio, Octave, Lumin, Aurender, MJ Acoustics"
        }
    ],
    "coimbatore": [
        {
            "name": "Cine Focus Coimbatore",
            "contact": "Mr. Sanjay",
            "phone": "+91 96555-57874",
            "address": "Coimbatore Region Partner, Tamilnadu",
            "brands": "ProAc, Kii Audio, System Audio"
        }
    ],
    "madurai": [
        {
            "name": "Jaksi Cinema",
            "contact": "Mr. Mohamed",
            "phone": "+91 86105-42082",
            "address": "Madurai Showroom Network, Tamilnadu",
            "brands": "ProAc, System Audio, Aurender"
        }
    ],
    "mumbai": [
        {
            "name": "Bombay Audio",
            "contact": "Mr. Ajay",
            "phone": "+91 79777-39128",
            "address": "Mumbai West Audition Lounge, Maharashtra",
            "brands": "ATC Hifi, ProAc, Ferrum"
        },
        {
            "name": "Tachyon Electrical & Control",
            "contact": "Mr. Jitendra",
            "phone": "+91 89752-09355",
            "address": "Mumbai Commercial, Maharashtra",
            "brands": "Hifirose, Eversolo"
        }
    ],
    "pune": [
        {
            "name": "Arcasonic Pvt Ltd",
            "contact": "Mr. Behram",
            "phone": "+91 98220-66943",
            "address": "Pune Central Listening Room, Maharashtra",
            "brands": "Hifirose, Octave"
        },
        {
            "name": "AVxellence Technologies",
            "contact": "Mr. Anand Lull",
            "phone": "+91 98509-82064",
            "address": "Pune Outer Ring, Maharashtra",
            "brands": "ATC Hifi, Eversolo, ProAc"
        }
    ],
    "delhi": [
        {
            "name": "SLR India",
            "contact": "Mr. Dipankar",
            "phone": "+91 98994-44687",
            "address": "New Delhi Premium Auditions, NCR",
            "brands": "ATC Hifi, Eversolo, Lumin"
        },
        {
            "name": "NA Marketing",
            "contact": "Mr. Abhishek",
            "phone": "+91 98111-65815",
            "address": "Delhi High End SCM Lounge, NCR",
            "brands": "ATC SCM High End Series, Hifirose"
        }
    ],
    "hyderabad": [
        {
            "name": "VV Devi Enterprises",
            "contact": "Mr. Navkash",
            "phone": "+91 74166-66699",
            "address": "Hyderabad Central, Telangana",
            "brands": "Lumin, Esoteric, Eversolo"
        },
        {
            "name": "Awicon Technologies LLP",
            "contact": "Mr. Vikas",
            "phone": "+91 88975-09199",
            "address": "Hyderabad IT Corridor Auditions, Telangana",
            "brands": "ATC Hifi, ProAc"
        }
    ],
    "bangalore": [
        {
            "name": "Soniq HIFI",
            "contact": "Mr. Nag",
            "phone": "+91 98456-15892",
            "address": "Bangalore Luxury Showroom, Karnataka",
            "brands": "Hifirose, Octave, Lumin"
        },
        {
            "name": "Mr. JNF Enterprises",
            "contact": "Mr. James",
            "phone": "+91 98800-26587",
            "address": "Bangalore Tech Auditions, Karnataka",
            "brands": "Eversolo, System Audio"
        }
    ],
    "alappuzha": [
        {
            "name": "The Audio Project",
            "contact": "Mr. Arun",
            "phone": "+91 93497-79812",
            "address": "Alappuzha Showroom Coast, Kerala",
            "brands": "Eversolo, Hifirose"
        }
    ],
    "kolkata": [
        {
            "name": "SKS Traders",
            "contact": "Mr. Bipra",
            "phone": "+91 98311-63529",
            "address": "Kolkata High-End Desk, West Bengal",
            "brands": "ATC Hifi, Eversolo, ProAc"
        }
    ]
};

// --- Initializing Application ---
document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize router
    initRouter();
    
    // 2. Load Cart from LocalStorage
    loadCartFromStorage();
    
    // 3. Populate Category list and Brands list
    initSidebarFilters();
    
    // 4. Render product catalog initially
    renderCatalog();
    
    // 5. Initialize dealers tab switcher
    initDealersTabs();
    
    // 6. Bind all interactive DOM listeners
    bindDOMEvents();
});

// --- Hash-Based Client Router ---
function initRouter() {
    const handleHashChange = () => {
        const hash = window.location.hash.slice(1) || 'home';
        switchTab(hash);
    };
    
    window.addEventListener("hashchange", handleHashChange);
    // Trigger initially
    handleHashChange();
}

function switchTab(tabId) {
    const sections = document.querySelectorAll(".view-section");
    const navLinks = document.querySelectorAll(".nav-link");
    
    // Validate target tab exists
    const targetSection = document.getElementById(`view-${tabId}`);
    if (!targetSection) return;
    
    // Deactivate previous, activate target
    sections.forEach(s => s.classList.remove("active"));
    targetSection.classList.add("active");
    
    // Update Nav bar highlights
    navLinks.forEach(link => {
        if (link.getAttribute("data-tab") === tabId) {
            link.classList.add("active");
        } else {
            link.classList.remove("active");
        }
    });
    
    currentTab = tabId;
    window.scrollTo({ top: 0, behavior: "smooth" });
    
    // Close mobile menu drawer if open
    document.getElementById("desktop-nav").classList.remove("open");
}

// --- Dynamic Sidebar Filters Init ---
function initSidebarFilters() {
    const categoryFilterList = document.getElementById("category-filter-list");
    const brandFilterList = document.getElementById("brand-filter-list");
    
    // Get unique categories and brands
    const categoriesMap = {};
    const brandsMap = {};
    
    productsData.forEach(p => {
        // Collect categories
        if (p.categories && Array.isArray(p.categories)) {
            p.categories.forEach(cat => {
                categoriesMap[cat] = (categoriesMap[cat] || 0) + 1;
            });
        }
        
        // Infer brands from categories or title tags
        const brandMatch = getProductBrand(p);
        brandsMap[brandMatch] = (brandsMap[brandMatch] || 0) + 1;
    });
    
    // 1. Render Categories Filter list
    let catHtml = `
        <div class="filter-item active" data-cat="all" onclick="selectCategory('all')">
            <span>All Categories</span>
            <span class="filter-count">${productsData.length}</span>
        </div>
    `;
    
    Object.keys(categoriesMap).sort().forEach(cat => {
        catHtml += `
            <div class="filter-item" data-cat="${cat}" onclick="selectCategory('${cat}')">
                <span>${cat}</span>
                <span class="filter-count">${categoriesMap[cat]}</span>
            </div>
        `;
    });
    categoryFilterList.innerHTML = catHtml;
    
    // 2. Render Brands Filter list
    let brandHtml = `
        <div class="filter-item active" data-brand="all" onclick="selectBrand('all')">
            <span>All Brands</span>
            <span class="filter-count">${productsData.length}</span>
        </div>
    `;
    
    Object.keys(brandsMap).sort().forEach(brand => {
        brandHtml += `
            <div class="filter-item" data-brand="${brand}" onclick="selectBrand('${brand}')">
                <span>${brand}</span>
                <span class="filter-count">${brandsMap[brand]}</span>
            </div>
        `;
    });
    brandFilterList.innerHTML = brandHtml;
}

function getProductBrand(product) {
    const titleLower = product.title.toLowerCase();
    
    if (titleLower.includes('kii')) return 'Kii Audio';
    if (titleLower.includes('proac') || titleLower.includes('pro ac')) return 'ProAc';
    if (titleLower.includes('audio vector') || titleLower.includes('audiovector')) return 'Audiovector';
    if (titleLower.includes('system audio') || titleLower.includes('saxo') || titleLower.includes('legend')) return 'System Audio';
    if (titleLower.includes('octave')) return 'Octave';
    if (titleLower.includes('lumin')) return 'Lumin';
    if (titleLower.includes('aurender')) return 'Aurender';
    if (titleLower.includes('mj acoustic') || titleLower.includes('mj acoustics')) return 'MJ Acoustics';
    if (titleLower.includes('eversolo')) return 'Eversolo';
    if (titleLower.includes('ferrum')) return 'Ferrum';
    if (titleLower.includes('hifirose') || titleLower.includes('rose')) return 'Hifirose';
    
    // Fallback search in categories
    if (product.categories) {
        for (let cat of product.categories) {
            const catLower = cat.toLowerCase();
            if (catLower.includes('proac')) return 'ProAc';
            if (catLower.includes('kii')) return 'Kii Audio';
            if (catLower.includes('audiovector')) return 'Audiovector';
            if (catLower.includes('system audio')) return 'System Audio';
            if (catLower.includes('octave')) return 'Octave';
            if (catLower.includes('lumin')) return 'Lumin';
            if (catLower.includes('mj acoustic')) return 'MJ Acoustics';
        }
    }
    
    return 'Other Brands';
}

// --- Dynamic Catalog Renderer ---
function renderCatalog() {
    const productsGrid = document.getElementById("shop-products-grid");
    const countText = document.getElementById("results-count-text");
    
    // Filter the products
    let filtered = productsData.filter(p => {
        // 1. Category Filter
        const matchesCategory = activeCategory === 'all' || 
            (p.categories && p.categories.includes(activeCategory));
            
        // 2. Brand Filter
        const productBrand = getProductBrand(p);
        const matchesBrand = activeBrand === 'all' || 
            productBrand.toLowerCase() === activeBrand.toLowerCase();
            
        // 3. Search Query Filter
        const titleMatch = p.title.toLowerCase().includes(searchQuery.toLowerCase());
        const skuMatch = p.sku && p.sku.toLowerCase().includes(searchQuery.toLowerCase());
        const excerptMatch = p.excerpt && p.excerpt.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesSearch = titleMatch || skuMatch || excerptMatch;
        
        return matchesCategory && matchesBrand && matchesSearch;
    });
    
    // Sort products
    if (currentSort === 'alpha-asc') {
        filtered.sort((a, b) => a.title.localeCompare(b.title));
    } else if (currentSort === 'alpha-desc') {
        filtered.sort((a, b) => b.title.localeCompare(a.title));
    }
    
    // Update Results count text
    countText.innerText = `Showing ${filtered.length} of ${productsData.length} audio products`;
    
    // Handle No Results state
    if (filtered.length === 0) {
        productsGrid.innerHTML = `
            <div class="no-results" style="grid-column: 1 / -1;">
                <div class="no-results-icon"><i class="fa-solid fa-volume-xmark"></i></div>
                <h3>No Premium Gears Found</h3>
                <p style="color: var(--text-secondary); margin-top: 0.5rem;">Try refining your query search or category filters.</p>
            </div>
        `;
        return;
    }
    
    // Render dynamic cards
    let gridHtml = '';
    filtered.forEach(p => {
        const inCart = cartItems.includes(p.id);
        const btnClass = inCart ? 'btn-secondary' : 'btn-primary';
        const btnText = inCart ? '<i class="fa-solid fa-check text-gold"></i> Added' : '<i class="fa-solid fa-plus"></i> Add to Enquiry';
        
        // Format price
        let priceStr = 'Price on Audition';
        if (p.price && p.price !== '') {
            const parsedPrice = parseFloat(p.price);
            if (!isNaN(parsedPrice)) {
                priceStr = '₹' + parsedPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 });
            }
        }
        
        // Main thumbnail resolving
        let mainImg = p.image || 'wp-content/themes/audib/assets/images/placeholder.jpg';
        
        gridHtml += `
            <div class="product-card glass-card">
                <div class="product-image-container">
                    <div class="product-badges">
                        <span class="badge-category">${getProductBrand(p)}</span>
                    </div>
                    <img src="${mainImg}" alt="${p.title}" class="product-img" onerror="this.src='wp-content/uploads/woocommerce-placeholder.png'">
                </div>
                <div class="product-info">
                    <h3 class="product-title" title="${p.title}">${p.title}</h3>
                    <div class="product-sku">SKU: ${p.sku || 'N/A'}</div>
                    <p class="product-excerpt">${p.excerpt || 'Authorized flagship high-end performance speaker/electronics component for high-fidelity auditions.'}</p>
                    
                    <div class="product-footer">
                        <span class="product-price text-gold">${priceStr}</span>
                    </div>
                    
                    <div class="card-actions">
                        <button class="${btnClass} btn-card-add" onclick="toggleCartItem('${p.id}', event)" id="btn-add-${p.id}">
                            ${btnText}
                        </button>
                        <button class="btn-card-view" onclick="openProductModal('${p.id}')" title="Quick View Specs">
                            <i class="fa-solid fa-expand"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    productsGrid.innerHTML = gridHtml;
}

// --- Active Filter Switchers ---
function selectCategory(catId) {
    activeCategory = catId;
    
    // Highlight category list selection
    const items = document.querySelectorAll("#category-filter-list .filter-item");
    items.forEach(el => {
        if (el.getAttribute("data-cat") === catId) {
            el.classList.add("active");
        } else {
            el.classList.remove("active");
        }
    });
    
    renderCatalog();
}

function selectBrand(brandId) {
    activeBrand = brandId;
    
    // Highlight brand list selection
    const items = document.querySelectorAll("#brand-filter-list .filter-item");
    items.forEach(el => {
        if (el.getAttribute("data-brand") === brandId) {
            el.classList.add("active");
        } else {
            el.classList.remove("active");
        }
    });
    
    renderCatalog();
}

// Global hook to support navbar brand showcase filter clicks
window.filterByBrand = function(brandSearch) {
    switchTab('shop');
    
    // Highlight correct filter in DOM
    const items = document.querySelectorAll("#brand-filter-list .filter-item");
    let matched = false;
    items.forEach(el => {
        const elBrand = el.getAttribute("data-brand").toLowerCase();
        if (elBrand === brandSearch.toLowerCase()) {
            el.classList.add("active");
            activeBrand = el.getAttribute("data-brand");
            matched = true;
        } else {
            el.classList.remove("active");
        }
    });
    
    if (!matched) {
        // Fallback for custom strings
        selectBrand('all');
    } else {
        renderCatalog();
    }
};

// --- Product Modal Renderer (Quick View) ---
function openProductModal(productId) {
    const product = productsData.find(p => p.id === productId);
    if (!product) return;
    
    const modalContent = document.getElementById("modal-body-content");
    const modal = document.getElementById("product-modal");
    
    const inCart = cartItems.includes(product.id);
    const btnClass = inCart ? 'btn-secondary' : 'btn-primary';
    const btnText = inCart ? '<i class="fa-solid fa-check text-gold"></i> Added to Enquiry' : '<i class="fa-solid fa-plus"></i> Add to Enquiry';
    
    // Resolve gallery list
    let thumbHtml = '';
    let mainImg = product.image || 'wp-content/themes/audib/assets/images/placeholder.jpg';
    
    // Generate thumbnail selection
    const galleryImages = [mainImg];
    if (product.gallery && Array.isArray(product.gallery)) {
        product.gallery.forEach(img => {
            if (img && img !== '' && !galleryImages.includes(img)) {
                galleryImages.push(img);
            }
        });
    }
    
    galleryImages.forEach((img, idx) => {
        const activeClass = idx === 0 ? 'active' : '';
        thumbHtml += `
            <div class="modal-thumbnail ${activeClass}" onclick="swapModalImage(this, '${img}')">
                <img src="${img}" alt="Thumbnail ${idx+1}" onerror="this.src='wp-content/uploads/woocommerce-placeholder.png'">
            </div>
        `;
    });
    
    // Format price
    let priceStr = 'Price on Request';
    if (product.price && product.price !== '') {
        const parsedPrice = parseFloat(product.price);
        if (!isNaN(parsedPrice)) {
            priceStr = '₹' + parsedPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 });
        }
    }
    
    modalContent.innerHTML = `
        <div class="modal-gallery">
            <div class="modal-main-image-wrapper">
                <img src="${mainImg}" alt="${product.title}" class="modal-main-image" id="modal-primary-img" onerror="this.src='wp-content/uploads/woocommerce-placeholder.png'">
            </div>
            <div class="modal-thumbnails">
                ${thumbHtml}
            </div>
        </div>
        <div class="modal-details">
            <div class="modal-badge-row">
                <span class="badge-category">${getProductBrand(product)}</span>
                ${product.categories ? product.categories.slice(0,2).map(c => `<span class="badge-category" style="border-color: var(--border-light); color: var(--text-secondary);">${c}</span>`).join('') : ''}
            </div>
            <h2 class="modal-title">${product.title}</h2>
            <div class="modal-sku">SKU Code: ${product.sku || 'SD-TBA'}</div>
            
            <div style="font-size: 1.6rem; font-weight: 700; color: var(--gold-accent); margin-bottom: 1.5rem;">${priceStr}</div>
            
            <h3 class="modal-desc-title">Product Description</h3>
            <div class="modal-desc">
                <p style="margin-bottom: 1rem;">${product.excerpt || 'This flagship series audio apparatus represents the highest state of physical acoustic technology. Designed to resolve absolute room boundary interference, providing pure holographic soundstage dynamics.'}</p>
                <p>${product.description || 'Pre-calibration and dedicated installation support is bundled with this luxury speaker or electronics setup. Our regional master engineers will configure the high-current parameters to deliver optimal acoustic linear responses.'}</p>
            </div>
            
            <div class="modal-actions">
                <button class="${btnClass}" style="width: 100%;" onclick="toggleCartItemFromModal('${product.id}', this)">
                    ${btnText}
                </button>
            </div>
        </div>
    `;
    
    modal.classList.add("open");
}

window.swapModalImage = function(thumbElement, imgSrc) {
    // Swap source
    document.getElementById("modal-primary-img").src = imgSrc;
    
    // Highlight thumbnail
    const thumbs = document.querySelectorAll(".modal-thumbnail");
    thumbs.forEach(t => t.classList.remove("active"));
    thumbElement.classList.add("active");
};

function toggleCartItemFromModal(productId, modalButton) {
    const isAdding = !cartItems.includes(productId);
    toggleCartItem(productId, null);
    
    if (isAdding) {
        modalButton.className = 'btn-secondary';
        modalButton.innerHTML = '<i class="fa-solid fa-check text-gold"></i> Added to Enquiry';
    } else {
        modalButton.className = 'btn-primary';
        modalButton.innerHTML = '<i class="fa-solid fa-plus"></i> Add to Enquiry';
    }
}

// --- Enquiry Cart Logic ---
function toggleCartItem(productId, event) {
    if (event) {
        event.stopPropagation();
    }
    
    const idx = cartItems.indexOf(productId);
    const badge = document.getElementById("cart-count");
    
    if (idx === -1) {
        // Add to cart
        cartItems.push(productId);
        showToast("Success", "Added to your quote proposal", "success");
        
        // Shake animation on badge
        badge.classList.add("shake");
        setTimeout(() => badge.classList.remove("shake"), 500);
    } else {
        // Remove from cart
        cartItems.splice(idx, 1);
        showToast("Removed", "Item removed from quote proposal");
    }
    
    // Persist
    saveCartToStorage();
    
    // Update Badge & Drawer
    updateCartUI();
    
    // Re-render catalog to sync buttons
    renderCatalog();
}

function updateCartUI() {
    const badge = document.getElementById("cart-count");
    badge.innerText = cartItems.length;
    
    const container = document.getElementById("cart-items-container");
    const drawerForm = document.getElementById("drawer-form-container");
    const btnQuote = document.getElementById("btn-show-quote-form");
    
    if (cartItems.length === 0) {
        container.innerHTML = `
            <div class="cart-empty">
                <div class="cart-empty-icon"><i class="fa-solid fa-receipt"></i></div>
                <h3>Your Enquiry Cart is Empty</h3>
                <p style="color: var(--text-secondary); margin-top: 0.5rem; font-size: 0.9rem;">Browse the catalog and add gears to request audition quotes.</p>
            </div>
        `;
        drawerForm.style.display = "none";
        btnQuote.style.display = "none";
        return;
    }
    
    let itemsHtml = '';
    cartItems.forEach(pid => {
        const p = productsData.find(prod => prod.id === pid);
        if (!p) return;
        
        let mainImg = p.image || 'wp-content/themes/audib/assets/images/placeholder.jpg';
        
        itemsHtml += `
            <div class="cart-item">
                <div class="cart-item-img-wrapper">
                    <img src="${mainImg}" alt="${p.title}" class="cart-item-img" onerror="this.src='wp-content/uploads/woocommerce-placeholder.png'">
                </div>
                <div class="cart-item-details">
                    <h4 class="cart-item-title">${p.title}</h4>
                    <span class="cart-item-sku">SKU: ${p.sku || 'SD-TBA'}</span>
                </div>
                <div class="cart-item-remove" onclick="toggleCartItem('${p.id}', event)">
                    <i class="fa-solid fa-circle-xmark"></i>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = itemsHtml;
    btnQuote.style.display = "block";
}

function saveCartToStorage() {
    localStorage.setItem("cf_enquiry_cart", JSON.stringify(cartItems));
}

function loadCartFromStorage() {
    const saved = localStorage.getItem("cf_enquiry_cart");
    if (saved) {
        try {
            cartItems = JSON.parse(saved);
            updateCartUI();
        } catch(e) {
            cartItems = [];
        }
    }
}

// --- Dynamic Dealers city lookup renderer ---
function initDealersTabs() {
    const cityTabsContainer = document.getElementById("dealer-city-tabs");
    const cities = Object.keys(dealersData);
    
    let tabsHtml = '';
    cities.forEach((city, idx) => {
        const activeClass = idx === 0 ? 'active' : '';
        tabsHtml += `
            <button class="city-tab ${activeClass}" data-city="${city}" onclick="selectDealerCity('${city}', this)">
                ${city.toUpperCase()}
            </button>
        `;
    });
    cityTabsContainer.innerHTML = tabsHtml;
    
    // Select first city by default
    if (cities.length > 0) {
        renderDealersForCity(cities[0]);
    }
}

window.selectDealerCity = function(cityKey, tabElement) {
    const tabs = document.querySelectorAll(".city-tab");
    tabs.forEach(t => t.classList.remove("active"));
    tabElement.classList.add("active");
    
    renderDealersForCity(cityKey);
};

function renderDealersForCity(cityKey) {
    const container = document.getElementById("dealers-container");
    const dealersList = dealersData[cityKey];
    
    if (!dealersList || dealersList.length === 0) {
        container.innerHTML = `<p style="text-align: center; color: var(--text-secondary);">No active dealers mapped in this region.</p>`;
        return;
    }
    
    let cardsHtml = '';
    dealersList.forEach(d => {
        cardsHtml += `
            <div class="dealer-card glass-card">
                <div class="dealer-details">
                    <h3>${d.name}</h3>
                    <div class="dealer-meta">
                        <div class="dealer-meta-item">
                            <i class="fa-solid fa-user-tie text-gold"></i>
                            <span>Liaison Desk: <strong>${d.contact}</strong></span>
                        </div>
                        <div class="dealer-meta-item">
                            <i class="fa-solid fa-map-pin text-gold"></i>
                            <span>${d.address}</span>
                        </div>
                        <div class="dealer-meta-item">
                            <i class="fa-solid fa-circle-nodes text-gold"></i>
                            <span style="font-size: 0.85rem; color: var(--text-muted);">Brands Handled: ${d.brands}</span>
                        </div>
                    </div>
                </div>
                
                <div class="dealer-actions" style="display: flex; flex-direction: column; gap: 0.8rem; align-items: flex-end;">
                    <a href="tel:${d.phone.replace(/[^0-9+]/g, '')}" class="btn-primary" style="padding: 0.6rem 1.2rem; font-size: 0.8rem;">
                        <i class="fa-solid fa-phone"></i> Call Partner
                    </a>
                    ${d.landline ? `<span style="font-size: 0.8rem; color: var(--text-secondary);">Landline: ${d.landline}</span>` : ''}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = cardsHtml;
}

// --- Mock Quote / Contact Submissions ---
window.handleFormSubmit = function(event, type) {
    event.preventDefault();
    
    if (type === 'contact') {
        showToast("Message Sent", "Our team will email you soon!", "success");
        event.target.reset();
    } else if (type === 'quote') {
        const quoteName = document.getElementById("quote-name").value;
        
        // Generate random Quote ID
        const randomDigits = Math.floor(100000 + Math.random() * 900000);
        const quoteId = `CF-${randomDigits}`;
        
        // Hide Drawer Panel
        closeDrawer();
        
        // Reset Cart
        cartItems = [];
        saveCartToStorage();
        updateCartUI();
        renderCatalog();
        
        // Show Success dialog
        document.getElementById("success-quote-id").innerText = quoteId;
        document.getElementById("quote-success-overlay").classList.add("active");
        
        // Reset form
        event.target.reset();
    }
};

window.closeSuccessOverlay = function() {
    document.getElementById("quote-success-overlay").classList.remove("active");
};

// --- Toast notification controllers ---
function showToast(title, message, type = 'info') {
    const stack = document.getElementById("toast-stack");
    
    const toast = document.createElement("div");
    toast.className = `toast glass-card ${type}`;
    
    const icon = type === 'success' ? '<i class="fa-solid fa-circle-check text-gold"></i>' : '<i class="fa-solid fa-circle-info"></i>';
    
    toast.innerHTML = `
        ${icon}
        <div>
            <div style="font-weight: 700; font-size: 0.85rem;">${title}</div>
            <div style="font-size: 0.75rem; color: var(--text-secondary);">${message}</div>
        </div>
        <span class="toast-close" onclick="this.parentElement.remove()">&times;</span>
    `;
    
    stack.appendChild(toast);
    
    // Auto remove after 4.5s
    setTimeout(() => {
        toast.style.animation = "toast-slide-in 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) reverse forwards";
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}

// --- Bind Interactive Events ---
function bindDOMEvents() {
    const mainHeader = document.getElementById("main-header");
    const cartBtn = document.getElementById("cart-btn");
    const drawerCloseBtn = document.getElementById("drawer-close-btn");
    const drawerOverlay = document.getElementById("cart-drawer-overlay");
    const modalCloseBtn = document.getElementById("modal-close-btn");
    const productModal = document.getElementById("product-modal");
    const resetFiltersBtn = document.getElementById("reset-filters-btn");
    const shopSearch = document.getElementById("shop-search");
    const shopSort = document.getElementById("shop-sort");
    const showQuoteFormBtn = document.getElementById("btn-show-quote-form");
    const drawerFormContainer = document.getElementById("drawer-form-container");
    const mobileToggle = document.getElementById("mobile-toggle");
    const desktopNav = document.getElementById("desktop-nav");
    
    // Sticky header shadow trigger
    window.addEventListener("scroll", () => {
        if (window.scrollY > 40) {
            mainHeader.classList.add("scrolled");
        } else {
            mainHeader.classList.remove("scrolled");
        }
    });
    
    // Mobile navigation panel burger toggle
    mobileToggle.addEventListener("click", () => {
        desktopNav.classList.toggle("open");
        // CSS rules inside index.css will handle navigation display under .open
    });
    
    // Nav links router hook
    const navLinks = document.querySelectorAll(".nav-link");
    navLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const tabId = link.getAttribute("data-tab");
            window.location.hash = tabId;
        });
    });
    
    // Logo redirect link
    document.getElementById("logo-nav").addEventListener("click", (e) => {
        e.preventDefault();
        window.location.hash = "home";
    });
    
    // Drawer open/close
    cartBtn.addEventListener("click", () => {
        drawerOverlay.classList.add("open");
    });
    
    drawerCloseBtn.addEventListener("click", closeDrawer);
    
    drawerOverlay.addEventListener("click", (e) => {
        if (e.target === drawerOverlay) closeDrawer();
    });
    
    function closeDrawer() {
        drawerOverlay.classList.remove("open");
        // Reset quote form toggle
        drawerFormContainer.style.display = "none";
        showQuoteFormBtn.style.display = cartItems.length > 0 ? "block" : "none";
    }
    
    // Modal close
    modalCloseBtn.addEventListener("click", closeModal);
    
    productModal.addEventListener("click", (e) => {
        if (e.target === productModal) closeModal();
    });
    
    function closeModal() {
        productModal.classList.remove("open");
    }
    
    // Show Quote form trigger
    showQuoteFormBtn.addEventListener("click", () => {
        drawerFormContainer.style.display = "block";
        showQuoteFormBtn.style.display = "none";
    });
    
    // Reset filters trigger
    resetFiltersBtn.addEventListener("click", () => {
        activeCategory = 'all';
        activeBrand = 'all';
        searchQuery = '';
        shopSearch.value = '';
        currentSort = 'default';
        shopSort.value = 'default';
        
        // Reset sidebars
        const catItems = document.querySelectorAll("#category-filter-list .filter-item");
        catItems.forEach(el => {
            if (el.getAttribute("data-cat") === 'all') el.classList.add("active");
            else el.classList.remove("active");
        });
        
        const brandItems = document.querySelectorAll("#brand-filter-list .filter-item");
        brandItems.forEach(el => {
            if (el.getAttribute("data-brand") === 'all') el.classList.add("active");
            else el.classList.remove("active");
        });
        
        renderCatalog();
        showToast("Filters Cleared", "Displaying all premium audio products.");
    });
    
    // Search filter input
    shopSearch.addEventListener("input", (e) => {
        searchQuery = e.target.value;
        renderCatalog();
    });
    
    // Sort filter
    shopSort.addEventListener("change", (e) => {
        currentSort = e.target.value;
        renderCatalog();
    });
}
