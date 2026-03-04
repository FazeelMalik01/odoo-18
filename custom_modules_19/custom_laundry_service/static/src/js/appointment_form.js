(function () {
    'use strict';

    function initServiceTypeSelect(serviceTypeSelect) {
        // If element is passed as parameter, use it; otherwise try to find it
        if (!serviceTypeSelect) {
            // Try plural first (correct one)
            serviceTypeSelect = document.getElementById('service_type_ids');
            if (!serviceTypeSelect) {
                serviceTypeSelect = document.querySelector('select[name="service_type_ids"]');
            }
            // Fallback to singular (in case template was changed or overridden)
            if (!serviceTypeSelect) {
                serviceTypeSelect = document.getElementById('service_type_id');
            }
            if (!serviceTypeSelect) {
                serviceTypeSelect = document.querySelector('select[name="service_type_id"]');
            }
        }

        if (!serviceTypeSelect) {
            return false; // Element not found, return silently
        }

        // Check if already initialized (has data attribute to prevent double initialization)
        if (serviceTypeSelect.hasAttribute('data-initialized')) {
            return true; // Already initialized
        }

        // Ensure the select is NOT multiple (single select)
        if (serviceTypeSelect.hasAttribute('multiple')) {
            serviceTypeSelect.removeAttribute('multiple');
            console.log('Fixed: Removed multiple attribute from select element');
        }

        console.log('Initializing service type select...', serviceTypeSelect);
        serviceTypeSelect.setAttribute('data-initialized', 'true');

        // Use Odoo's JSON-RPC format
        // Get CSRF token from form or cookie
        function getCSRFToken() {
            // Try to get from form input (most reliable in portal)
            const csrfInput = document.querySelector('input[name="csrf_token"]');
            if (csrfInput) {
                return csrfInput.value;
            }
            // Try to get from meta tag
            const metaTag = document.querySelector('meta[name="csrf-token"]');
            if (metaTag) {
                return metaTag.getAttribute('content');
            }
            return '';
        }

        // Prepare JSON-RPC request
        const csrfToken = getCSRFToken();
        const jsonRpcRequest = {
            jsonrpc: '2.0',
            method: 'call',
            params: {},
            id: Math.floor(Math.random() * 1000000000)
        };

        // Make JSON-RPC call
        console.log('Sending JSON-RPC request to /my/appointments/get_service_products');
        fetch('/my/appointments/get_service_products', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(jsonRpcRequest)
        })
            .then(response => {
                console.log('Response received:', response.status, response.statusText);
                if (!response.ok) {
                    throw new Error('Network response was not ok: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                console.log('Response data:', data);
                // Handle JSON-RPC response format
                // Odoo returns {result: data} or {error: ...}
                if (data.error) {
                    console.error('JSON-RPC Error:', data.error);
                    throw new Error(data.error.message || data.error.data?.message || 'Server error');
                }
                const products = data.result || [];
                console.log('Products received:', products);
                if (Array.isArray(products)) {
                    // Filter products to only include those with service_size set (small, medium, large)
                    // Exclude ironing products (small_ironing, medium_ironing, large_ironing) as they are shown separately as a checkbox
                    const filteredProducts = products.filter(product => {
                        const serviceSize = product.service_size;
                        // Only include products where service_size is set and is one of: small, medium, or large
                        // Exclude all ironing products (they are shown as a separate checkbox)
                        return serviceSize && ['small', 'medium', 'large'].includes(serviceSize);
                    });
                    console.log('Filtered products (with service_size, excluding ironing):', filteredProducts);
                    populateSelect(serviceTypeSelect, filteredProducts);
                } else {
                    throw new Error('Invalid response format');
                }
            })
            .catch(error => {
                console.error('Error loading service products:', error);
                serviceTypeSelect.innerHTML = '<option value="">Error loading service types. Please refresh the page.</option>';
            });

        // Return true to indicate element was found and initialization started
        return true;
    }

    function initIroningProductCheckbox() {
        const ironingCheckbox = document.getElementById('ironing_product_id');
        const ironingLabel = document.getElementById('ironing_product_label');
        const ironingContainer = document.getElementById('ironing_product_container');
        const serviceTypeSelect = document.getElementById('service_type_ids');
        
        if (!ironingCheckbox || !ironingLabel || !ironingContainer) {
            return false;
        }

        // Check if already initialized
        if (ironingCheckbox.hasAttribute('data-initialized')) {
            return true;
        }

        ironingCheckbox.setAttribute('data-initialized', 'true');

        // Get all ironing products from data attribute
        const ironingProductsData = ironingContainer.getAttribute('data-ironing-products');
        let ironingProducts = {};
        
        if (ironingProductsData) {
            try {
                ironingProducts = JSON.parse(ironingProductsData);
            } catch (e) {
                console.error('Error parsing ironing products data:', e);
            }
        }

        // Function to update ironing checkbox based on selected service type
        function updateIroningCheckbox() {
            if (!serviceTypeSelect || !serviceTypeSelect.value) {
                ironingContainer.style.display = 'none';
                ironingCheckbox.checked = false;
                return;
            }

            // Get the selected product's service_size
            const selectedOption = serviceTypeSelect.options[serviceTypeSelect.selectedIndex];
            const selectedProductId = selectedOption.value;
            const selectedServiceSize = selectedOption.getAttribute('data-service-size');

            if (!selectedServiceSize) {
                ironingContainer.style.display = 'none';
                ironingCheckbox.checked = false;
                return;
            }

            // Map service size to ironing size: small -> small_ironing, medium -> medium_ironing, large -> large_ironing
            const ironingSizeMap = {
                'small': 'small_ironing',
                'medium': 'medium_ironing',
                'large': 'large_ironing'
            };

            const matchingIroningSize = ironingSizeMap[selectedServiceSize];
            
            if (matchingIroningSize && ironingProducts[matchingIroningSize]) {
                const ironingProduct = ironingProducts[matchingIroningSize];
                ironingCheckbox.value = ironingProduct.id;
                ironingLabel.textContent = ironingProduct.name;
                ironingContainer.style.display = 'block';
                
                // Check if checkbox should be checked (from data-checked attribute)
                const checkedAttr = ironingCheckbox.getAttribute('data-checked');
                if (checkedAttr && (checkedAttr === 'true' || checkedAttr === ironingProduct.id.toString())) {
                    ironingCheckbox.checked = true;
                } else {
                    ironingCheckbox.checked = false;
                }
            } else {
                ironingContainer.style.display = 'none';
                ironingCheckbox.checked = false;
            }
        }

        // Listen to service type changes
        if (serviceTypeSelect) {
            serviceTypeSelect.addEventListener('change', updateIroningCheckbox);
            
            // Also update on initial load if a service type is already selected
            if (serviceTypeSelect.value) {
                updateIroningCheckbox();
            }
        } else {
            // Hide if no service type select found
            ironingContainer.style.display = 'none';
        }

        return true;
    }

    function populateSelect(serviceTypeSelect, products) {
        // Clear loading message
        serviceTypeSelect.innerHTML = '';

        // Add empty option first
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = 'Select a service type...';
        serviceTypeSelect.appendChild(emptyOption);

        // Get selected value if editing (single ID)
        const selectedValueAttr = serviceTypeSelect.getAttribute('data-selected-value');
        let selectedValue = null;
        if (selectedValueAttr) {
            try {
                // Try to parse as JSON first (in case it's a string representation of a number)
                selectedValue = JSON.parse(selectedValueAttr);
            } catch (e) {
                // If not JSON, use as-is
                selectedValue = selectedValueAttr;
            }
            // Convert to string for comparison
            selectedValue = String(selectedValue);
        }

        // Get preselected product ID from URL parameter or data attribute
        const preselectedProductIdAttr = serviceTypeSelect.getAttribute('data-preselected-product-id');
        let preselectedProductId = null;
        if (preselectedProductIdAttr) {
            preselectedProductId = String(preselectedProductIdAttr);
        } else {
            // Try to get from URL parameter
            const urlParams = new URLSearchParams(window.location.search);
            const productIdParam = urlParams.get('product_id');
            if (productIdParam) {
                preselectedProductId = String(productIdParam);
            }
        }

        // Use preselected product ID if no selected value from editing
        if (!selectedValue && preselectedProductId) {
            selectedValue = preselectedProductId;
        }

        // Populate options
        products.forEach(product => {
            const option = document.createElement('option');
            option.value = product.id;
            option.textContent = product.name;
            
            // Add data-service-size attribute for ironing checkbox matching
            if (product.service_size) {
                option.setAttribute('data-service-size', product.service_size);
            }

            // Set selected if editing or if preselected from pricing page
            if (selectedValue && String(product.id) === selectedValue) {
                option.selected = true;
            }

            serviceTypeSelect.appendChild(option);
        });
        
        // After populating, trigger ironing checkbox update if service type is already selected
        if (serviceTypeSelect.value) {
            setTimeout(function() {
                const ironingContainer = document.getElementById('ironing_product_container');
                const ironingCheckbox = document.getElementById('ironing_product_id');
                const ironingLabel = document.getElementById('ironing_product_label');
                
                if (!ironingContainer || !ironingCheckbox || !ironingLabel) {
                    return;
                }
                
                const selectedOption = serviceTypeSelect.options[serviceTypeSelect.selectedIndex];
                const selectedServiceSize = selectedOption ? selectedOption.getAttribute('data-service-size') : null;
                
                if (!selectedServiceSize) {
                    ironingContainer.style.display = 'none';
                    ironingCheckbox.checked = false;
                    return;
                }
                
                const ironingProductsData = ironingContainer.getAttribute('data-ironing-products');
                let ironingProducts = {};
                
                if (ironingProductsData) {
                    try {
                        ironingProducts = JSON.parse(ironingProductsData);
                    } catch (e) {
                        console.error('Error parsing ironing products data:', e);
                    }
                }
                
                const ironingSizeMap = {
                    'small': 'small_ironing',
                    'medium': 'medium_ironing',
                    'large': 'large_ironing'
                };
                
                const matchingIroningSize = ironingSizeMap[selectedServiceSize];
                
                if (matchingIroningSize && ironingProducts[matchingIroningSize]) {
                    const ironingProduct = ironingProducts[matchingIroningSize];
                    ironingCheckbox.value = ironingProduct.id;
                    ironingLabel.textContent = ironingProduct.name;
                    ironingContainer.style.display = 'block';
                } else {
                    ironingContainer.style.display = 'none';
                }
            }, 100);
        }

        // Add validation for single select
        serviceTypeSelect.addEventListener('change', function () {
            if (!this.value || this.value === '') {
                this.setCustomValidity('Please select a service type.');
            } else {
                this.setCustomValidity('');
            }
        });

        // No need for custom dropdown UI for single select - use native select
    }

    // No custom dropdown needed for single select - using native select

    // Wait for element to appear using MutationObserver
    function waitForElement() {
        // Only run on pages that might have the appointment form
        const path = window.location.pathname;
        if (!path.includes('/my/appointments')) {
            return; // Not on appointments pages, exit silently
        }

        let found = false;
        let observer = null;
        let intervalId = null;
        let attempts = 0;
        const maxAttempts = 100; // 10 seconds (reduced from 20)

        const stopObserving = function () {
            if (observer) {
                observer.disconnect();
                observer = null;
            }
            if (intervalId) {
                clearInterval(intervalId);
                intervalId = null;
            }
        };

        const checkAndInit = function () {
            if (found) {
                return true; // Already initialized
            }

            // Try multiple search methods
            let serviceTypeSelect = document.getElementById('service_type_ids');
            if (!serviceTypeSelect) {
                serviceTypeSelect = document.querySelector('select[name="service_type_ids"]');
            }
            // Fallback to singular (in case template was changed)
            if (!serviceTypeSelect) {
                serviceTypeSelect = document.getElementById('service_type_id');
            }
            if (!serviceTypeSelect) {
                serviceTypeSelect = document.querySelector('select[name="service_type_id"]');
            }
            if (!serviceTypeSelect) {
                // Try finding any select with service_type_ids name in the form
                const form = document.querySelector('form[action="/my/appointments/book"]');
                if (form) {
                    serviceTypeSelect = form.querySelector('select[name="service_type_ids"]');
                }
            }

            if (serviceTypeSelect) {
                if (initServiceTypeSelect(serviceTypeSelect)) {
                    found = true;
                    stopObserving();
                    return true;
                }
            }
            return false;
        };

        // First, try immediately
        if (checkAndInit()) {
            return; // Success!
        }

        // MutationObserver to watch for DOM changes
        if (document.body) {
            observer = new MutationObserver(function (mutations, obs) {
                if (checkAndInit()) {
                    console.log('Element found via MutationObserver');
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        } else {
            // Wait for body to be available
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function () {
                    if (document.body && !found) {
                        observer = new MutationObserver(function (mutations, obs) {
                            if (checkAndInit()) {
                                console.log('Element found via MutationObserver');
                            }
                        });
                        observer.observe(document.body, {
                            childList: true,
                            subtree: true
                        });
                    }
                });
            }
        }

        // Fallback: also try with intervals as backup (but log less frequently)
        intervalId = setInterval(function () {
            attempts++;
            if (checkAndInit()) {
                // Already stopped by checkAndInit
            } else if (attempts >= maxAttempts) {
                // Only log error if we're on the booking page
                if (path.includes('/my/appointments/book')) {
                    console.error('Service type select element not found after maximum attempts. Current URL:', path);

                    // Debug: Log what select elements exist on the page
                    const allSelects = document.querySelectorAll('select');
                    console.log('Found', allSelects.length, 'select elements on page:');
                    allSelects.forEach((sel, idx) => {
                        console.log(`  Select ${idx + 1}: id="${sel.id}", name="${sel.name}", multiple="${sel.multiple}"`);
                    });

                    // Try one more time with various selectors (including singular)
                    let select = document.querySelector('select[name="service_type_ids"]');
                    if (!select) {
                        select = document.getElementById('service_type_ids');
                    }
                    // Try singular as fallback
                    if (!select) {
                        select = document.querySelector('select[name="service_type_id"]');
                    }
                    if (!select) {
                        select = document.getElementById('service_type_id');
                    }
                    if (!select) {
                        const form = document.querySelector('form[action="/my/appointments/book"]');
                        if (form) {
                            select = form.querySelector('select[name="service_type_ids"]');
                        }
                    }
                    if (select) {
                        console.log('Found element using fallback search, initializing...', select);
                        if (initServiceTypeSelect(select)) {
                            found = true;
                            stopObserving();
                        }
                    } else {
                        console.error('Element truly not found. Form exists:', !!document.querySelector('form[action="/my/appointments/book"]'));
                    }
                }
                stopObserving();
            }
        }, 100);
    }

    // Initialize form validation
    function initFormValidation() {
        const form = document.getElementById('appointment-booking-form');
        if (!form) {
            return;
        }

        form.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopPropagation();

            // Hide previous validation errors
            const validationErrorDiv = document.getElementById('form-validation-error');
            const errorList = document.getElementById('validation-error-list');
            if (validationErrorDiv) {
                validationErrorDiv.style.display = 'none';
            }
            if (errorList) {
                errorList.innerHTML = '';
            }

            // Clear previous validation states
            form.querySelectorAll('.is-invalid').forEach(el => {
                el.classList.remove('is-invalid');
            });

            // Validate all required fields
            const errors = [];
            const requiredFields = [
                { id: 'customer_name', name: 'Customer Name' },
                { id: 'mobile', name: 'Mobile' },
                { id: 'service_type_ids', name: 'Service Type' },
                { id: 'appointment_date', name: 'Date' },
                { id: 'time_slot_id', name: 'Time Slot' }
            ];

            requiredFields.forEach(field => {
                const element = document.getElementById(field.id);
                if (element) {
                    let isValid = true;

                    if (field.id === 'service_type_ids') {
                        // Check if service type is selected
                        if (!element.value || element.value === '') {
                            isValid = false;
                        }
                    } else if (field.id === 'time_slot_id') {
                        // Check if time slot is selected and not disabled
                        if (element.disabled || !element.value || element.value === '') {
                            isValid = false;
                        }
                    } else {
                        // Standard required field validation
                        if (!element.value || element.value.trim() === '') {
                            isValid = false;
                        }
                    }

                    if (!isValid) {
                        element.classList.add('is-invalid');
                        errors.push(field.name);
                    } else {
                        element.classList.remove('is-invalid');
                        element.classList.add('is-valid');
                    }
                }
            });

            // If there are errors, show them
            if (errors.length > 0) {
                if (validationErrorDiv) {
                    validationErrorDiv.style.display = 'block';
                }
                if (errorList) {
                    errors.forEach(error => {
                        const li = document.createElement('li');
                        li.textContent = error;
                        errorList.appendChild(li);
                    });
                }

                // Scroll to first error
                const firstError = form.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstError.focus();
                }

                return false;
            }

            // If validation passes, submit the form
            form.classList.add('was-validated');
            form.submit();
        });

        // Real-time validation on blur
        const requiredInputs = form.querySelectorAll('input[required], select[required]');
        requiredInputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.value && this.value.trim() !== '') {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    if (this.hasAttribute('required')) {
                        this.classList.add('is-invalid');
                    }
                }
            });

            input.addEventListener('input', function() {
                if (this.value && this.value.trim() !== '') {
                    this.classList.remove('is-invalid');
                }
            });
        });
    }

    // Initialize country-state dependency
    function initCountryStateDependency() {
        const countrySelect = document.getElementById('pickup_country_id');
        const stateSelect = document.getElementById('pickup_state_id');
        
        if (!countrySelect || !stateSelect) {
            return;
        }
        
        // Function to load states for a country
        function loadStatesForCountry(countryId, preserveSelectedStateId) {
            // Clear state dropdown
            stateSelect.innerHTML = '<option value="">Loading states...</option>';
            stateSelect.disabled = true;
            
            if (!countryId) {
                stateSelect.innerHTML = '<option value="">Select Country first...</option>';
                return;
            }
            
            // Fetch states for selected country
            const jsonRpcRequest = {
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    country_id: parseInt(countryId)
                },
                id: Math.floor(Math.random() * 1000000000)
            };
            
            fetch('/my/appointments/get_states', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(jsonRpcRequest)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading states:', data.error);
                        stateSelect.innerHTML = '<option value="">Error loading states</option>';
                        return;
                    }
                    
                    const states = data.result?.states || [];
                    
                    // Populate state dropdown
                    stateSelect.innerHTML = '<option value="">Select State/Province...</option>';
                    states.forEach(state => {
                        const option = document.createElement('option');
                        option.value = state.id;
                        option.textContent = state.name;
                        // Preserve selected state if provided
                        if (preserveSelectedStateId && String(state.id) === String(preserveSelectedStateId)) {
                            option.selected = true;
                        }
                        stateSelect.appendChild(option);
                    });
                    
                    // Enable state dropdown
                    stateSelect.disabled = false;
                })
                .catch(error => {
                    console.error('Error loading states:', error);
                    stateSelect.innerHTML = '<option value="">Error loading states</option>';
                });
        }
        
        // Handle country change
        countrySelect.addEventListener('change', function() {
            const countryId = this.value;
            loadStatesForCountry(countryId, null);
        });
        
        // If country is already selected on page load, load states and preserve selected state
        if (countrySelect.value) {
            // Get the selected state ID from data attribute or current value
            const selectedStateId = stateSelect.getAttribute('data-selected-state-id') || stateSelect.value;
            loadStatesForCountry(countrySelect.value, selectedStateId);
        }
    }

    // Start waiting when script loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            waitForElement();
            // Also initialize ironing checkbox
            setTimeout(initIroningProductCheckbox, 100);
            // Initialize form validation
            setTimeout(initFormValidation, 200);
            // Initialize country-state dependency
            setTimeout(initCountryStateDependency, 300);
        });
    } else {
        // DOM already loaded, but element might not be rendered yet
        waitForElement();
        // Also initialize ironing checkbox
        setTimeout(initIroningProductCheckbox, 100);
        // Initialize form validation
        setTimeout(initFormValidation, 200);
        // Initialize country-state dependency
        setTimeout(initCountryStateDependency, 300);
    }
})();

// Handle cancel appointment buttons
(function () {
    'use strict';

    function initCancelButtons() {
        const cancelButtons = document.querySelectorAll('.cancel-appointment');

        cancelButtons.forEach(function (button) {
            button.addEventListener('click', function () {
                const appointmentId = this.getAttribute('data-appointment-id');

                // Confirm cancellation
                if (!confirm('Are you sure you want to cancel this appointment?')) {
                    return;
                }

                // Disable button while processing
                this.disabled = true;
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Cancelling...';

                // Prepare JSON-RPC request
                const jsonRpcRequest = {
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        appointment_id: parseInt(appointmentId)
                    },
                    id: Math.floor(Math.random() * 1000000000)
                };

                // Send cancellation request
                fetch('/my/appointments/cancel', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(jsonRpcRequest)
                })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Network response was not ok: ' + response.status);
                        }
                        return response.json();
                    })
                    .then(data => {
                        // Handle JSON-RPC response format
                        if (data.error) {
                            console.error('Error cancelling appointment:', data.error);
                            const errorMsg = data.error.message || data.error.data?.message || 'Unknown error';
                            alert('Error cancelling appointment: ' + errorMsg);
                            this.innerHTML = originalText;
                            this.disabled = false;
                        } else if (data.result) {
                            const result = data.result;
                            if (result.success) {
                                // Success - reload page to show updated status
                                window.location.reload();
                            } else {
                                alert('Error cancelling appointment. Please try again.');
                                this.innerHTML = originalText;
                                this.disabled = false;
                            }
                        } else {
                            throw new Error('Unexpected response format');
                        }
                    })
                    .catch(error => {
                        console.error('Error cancelling appointment:', error);
                        alert('Error cancelling appointment. Please try again.');
                        this.innerHTML = originalText;
                        this.disabled = false;
                    });
            });
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCancelButtons);
    } else {
        initCancelButtons();
    }
})();

