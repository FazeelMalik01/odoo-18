/** @odoo-module **/

// Use native DOM ready event
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeLazyLoad);
} else {
    initializeLazyLoad();
}

function initializeLazyLoad() {
    const productsPage = document.querySelector('.o_wsale_products_page');
    if (!productsPage) return;

    // Get initial values
    const section = document.querySelector('.o_wsale_products_grid_table_wrapper > section');
    const initialppg = section ? parseInt(section.getAttribute('data-ppg')) || 20 : 20;
    let currentPage = getCurrentPage();
    let loading = false;
    let isNextPageAvailable = true;

    // Setup button click handler
    const loadButton = document.querySelector('.wt-lazy-load-button');
    if (loadButton) {
        loadButton.addEventListener('click', onLoadMoreClick);
    }

    // Setup scroll handler for infinite scroll
    const scrollLoader = document.querySelector('.wt_website_product_lazy_load_scroll');
    if (scrollLoader) {
        window.addEventListener('scroll', debounce(onScroll, 200));
    }

    function getCurrentPage() {
        const path = window.location.pathname;
        const pageMatch = path.match(/\/page\/(\d+)/);
        return pageMatch ? parseInt(pageMatch[1], 10) : 1;
    }

    function getNextPageUrl() {
        const url = new URL(window.location.href);
        const params = new URLSearchParams(url.search);
        let currentPath = url.pathname;

        const langMatch = currentPath.match(/^\/([a-z]{2})\/shop/);
        const isLocalized = langMatch !== null;
        const nextPage = currentPage + 1;

        if (isLocalized) {
            if (currentPath.match(/\/page\/\d+/)) {
                currentPath = currentPath.replace(/\/page\/\d+/, `/page/${nextPage}`);
            } else {
                currentPath = currentPath.replace(/\/shop/, `/shop/page/${nextPage}`);
            }
            url.pathname = currentPath.replace(/\/shop/, '/shop-lazy');
        } else {
            if (currentPath.match(/\/page\/\d+/)) {
                url.pathname = currentPath.replace(/\/page\/\d+/, `/page/${nextPage}`);
            } else {
                url.pathname = `${currentPath}/page/${nextPage}`;
            }
            url.pathname = url.pathname.replace(/\/shop/, '/shop-lazy');
        }

        params.set('ppg', initialppg);
        url.search = params.toString();

        return url.toString();
    }

    async function fetchProductsAndRender() {
        if (loading) return 0;

        loading = true;
        const url = getNextPageUrl();

        // Show loading indicator
        showLoading(true);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Odoo-Session-Id': odoo.session_id,
                },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: { ppg: initialppg }
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            if (result.result && result.result.success && result.result.tableWrapper) {
                const temp = document.createElement('div');
                temp.innerHTML = result.result.tableWrapper;
                const newProducts = temp.querySelectorAll('.oe_product');

                const target = document.getElementById('o_wsale_products_grid') ||
                             document.querySelector('.o_wsale_products_grid_table_wrapper section');

                if (target && newProducts.length > 0) {
                    newProducts.forEach(product => target.appendChild(product));
                    currentPage++;

                    // Trigger events for plugins
                    document.dispatchEvent(new Event('content_changed'));
                    window.dispatchEvent(new Event('resize'));
                }

                loading = false;
                showLoading(false);
                return newProducts.length;
            } else {
                throw new Error(result.result?.error || 'Invalid response format');
            }
        } catch (error) {
            console.error("Fetch error:", error);
            showError('Failed to load more products. Please try again.');
            loading = false;
            showLoading(false);
            return 0;
        }
    }

    function showLoading(show) {
        const scrollLoader = document.querySelector('.wt_website_product_lazy_load_scroll');
        if (scrollLoader) {
            scrollLoader.classList.toggle('d-none', !show);
        }

        // Also handle button spinner
        const button = document.querySelector('.wt-lazy-load-button');
        if (button) {
            const spinner = button.querySelector('.spinner-grow');
            if (spinner) {
                spinner.classList.toggle('d-none', !show);
            }
            button.disabled = show;
        }
    }

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
        errorDiv.setAttribute('role', 'alert');
        errorDiv.innerHTML = `
            <i class="fa fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        const wrapper = document.querySelector('.o_wsale_products_grid_table_wrapper');
        if (wrapper) {
            wrapper.parentNode.insertBefore(errorDiv, wrapper);
            setTimeout(() => errorDiv.remove(), 5000);
        }
    }

    function debounce(func, wait) {
        let timeout;
        return function() {
            clearTimeout(timeout);
            timeout = setTimeout(func, wait);
        };
    }

    async function onScroll() {
        if (loading || !isNextPageAvailable) return;

        const scrollTop = window.scrollY;
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;

        // Load when 500px from bottom
        if (scrollTop + windowHeight >= documentHeight - 500) {
            const count = await fetchProductsAndRender();
            isNextPageAvailable = count >= initialppg;
            if (!isNextPageAvailable) {
                const btn = document.querySelector('.wt-lazy-load-button');
                if (btn) btn.style.display = 'none';
            }
        }
    }

    async function onLoadMoreClick(ev) {
        ev.preventDefault();
        if (loading || !isNextPageAvailable) return;

        const count = await fetchProductsAndRender();
        isNextPageAvailable = count >= initialppg;

        if (!isNextPageAvailable) {
            const btn = document.querySelector('.wt-lazy-load-button');
            if (btn) btn.style.display = 'none';
        }
    }
}