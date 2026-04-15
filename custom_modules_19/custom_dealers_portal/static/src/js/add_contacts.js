(function () {
    'use strict';

    // Helper function to get CSRF token
    function getCsrfToken() {
        if (window.odoo && window.odoo.csrf_token) {
            return window.odoo.csrf_token;
        }
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta && csrfMeta.content) {
            return csrfMeta.content;
        }
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput && csrfInput.value) {
            return csrfInput.value;
        }
        console.warn('CSRF token not found');
        return '';
    }

    // Initialize when DOM is ready
    function initCustomerForm() {
        const addBtn = document.getElementById('add_customer_btn');
        const formRow = document.getElementById('customer_form_row');
        const saveBtn = document.getElementById('save_customer_btn');
        const cancelBtn = document.getElementById('cancel_customer_btn');
        const customerIdInput = document.getElementById('customer_id');
        const hasCompanySelect = document.getElementById('customer_has_company');
        const companyFields = document.querySelectorAll('.customer-company-fields');
        const companyNameInput = document.getElementById('customer_company_name');
        const companyAddressInput = document.getElementById('customer_company_address');

        if (!addBtn || !formRow || !saveBtn) {
            console.warn('Customer form elements not found');
            return;
        }

        console.log('✅ Customers portal JS loaded');

        function toggleCompanyFields() {
            const showCompanyFields = hasCompanySelect && hasCompanySelect.value === 'true';
            companyFields.forEach(function (field) {
                field.classList.toggle('d-none', !showCompanyFields);
            });
            if (!showCompanyFields) {
                if (companyNameInput) companyNameInput.value = '';
                if (companyAddressInput) companyAddressInput.value = '';
            }
        }

        if (hasCompanySelect) {
            hasCompanySelect.addEventListener('change', toggleCompanyFields);
        }

        // Show add form
        addBtn.addEventListener('click', function () {
            resetForm();
            document.getElementById('form_title').textContent = 'Add New Customer';
            formRow.classList.remove('d-none');
            addBtn.classList.add('d-none');
            toggleCompanyFields();
        });

        // Cancel form
        if (cancelBtn) {
            cancelBtn.addEventListener('click', function () {
                formRow.classList.add('d-none');
                addBtn.classList.remove('d-none');
                resetForm();
            });
        }

        // Save customer (add or update)
        saveBtn.addEventListener('click', function () {
            const customerId = customerIdInput ? customerIdInput.value : '';
            const name = document.getElementById('customer_name').value.trim();
            const email = document.getElementById('customer_email').value.trim();
            const phone = document.getElementById('customer_phone').value.trim();
            const mobile_number = document.getElementById('customer_mobile').value.trim();
            const comment = document.getElementById('customer_comment').value.trim();
            const shipping_option = document.getElementById('customer_shipping_option').value;
            const has_customer_company = hasCompanySelect ? hasCompanySelect.value === 'true' : false;
            const customer_company_name = companyNameInput ? companyNameInput.value.trim() : '';
            const customer_company_address = companyAddressInput ? companyAddressInput.value.trim() : '';

            if (!name) {
                alert('Customer name is required');
                return;
            }
            if (has_customer_company && !customer_company_name) {
                alert('Company name is required when customer has a company');
                return;
            }
            if (has_customer_company && !customer_company_address) {
                alert('Company address is required when customer has a company');
                return;
            }

            const requestData = {
                name: name,
                email: email || '',
                phone: phone || '',
                mobile_number: mobile_number || '',
                comment: comment || '',
                shipping_option_dropship: shipping_option || '',
                has_customer_company: has_customer_company,
                customer_company_name: customer_company_name || '',
                customer_company_address: customer_company_address || '',
            };

            let url = '/my/add_customer';
            let isUpdate = false;
            if (customerId) {
                url = '/my/update_customer';
                requestData.customer_id = parseInt(customerId);
                isUpdate = true;
            }

            const csrfToken = getCsrfToken();
            const originalText = saveBtn.textContent;
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRF-TOKEN': csrfToken,
                },
                body: JSON.stringify(requestData),
            })
            .then(res => {
                if (!res.ok) {
                    throw new Error(`HTTP error! Status: ${res.status}`);
                }
                return res.json();
            })
            .then(data => {
                if (data.success === false) {
                    alert('Error: ' + (data.error || 'Failed to save customer'));
                    return;
                }
                alert(isUpdate ? 'Customer updated successfully!' : 'Customer added successfully!');
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to save customer. Please try again.');
            })
            .finally(() => {
                saveBtn.disabled = false;
                saveBtn.textContent = originalText;
            });
        });

        // Edit button handler - simple event delegation
        document.body.addEventListener('click', function(e) {
            // Check if clicked element or parent has edit-customer-btn class
            let editBtn = null;
            if (e.target.classList.contains('edit-customer-btn')) {
                editBtn = e.target;
            } else if (e.target.closest('.edit-customer-btn')) {
                editBtn = e.target.closest('.edit-customer-btn');
            }
            
            if (editBtn) {
                e.preventDefault();
                e.stopPropagation();
                
                const customerId = editBtn.getAttribute('data-customer-id');
                console.log('Edit clicked for customer:', customerId);
                
                if (!customerId) {
                    console.error('No customer ID found');
                    return;
                }

                // Find the row - try multiple methods
                let row = document.getElementById('customer_row_' + customerId);
                if (!row) {
                    // Try finding by traversing up from button
                    row = editBtn.closest('tr');
                }
                
                if (!row) {
                    console.error('Row not found for customer:', customerId);
                    return;
                }

                // Get cell values
                const nameCell = row.querySelector('.customer-name');
                const emailCell = row.querySelector('.customer-email');
                const phoneCell = row.querySelector('.customer-phone');
                const mobileCell = row.querySelector('.customer-mobile');
                const commentCell = row.querySelector('.customer-comment');
                const shippingOptionCell = row.querySelector('.customer-shipping-option');

                const currentName = nameCell ? nameCell.textContent.trim() : '';
                const currentEmail = emailCell ? (emailCell.textContent.trim() === 'N/A' ? '' : emailCell.textContent.trim()) : '';
                const currentPhone = phoneCell ? (phoneCell.textContent.trim() === 'N/A' ? '' : phoneCell.textContent.trim()) : '';
                const currentMobile = mobileCell ? (mobileCell.textContent.trim() === 'N/A' ? '' : mobileCell.textContent.trim()) : '';
                const currentComment = commentCell ? (commentCell.textContent.trim() === 'N/A' ? '' : commentCell.textContent.trim()) : '';
                const rowHasCompany = row.getAttribute('data-has-company') === 'true';
                const rowCompanyName = row.getAttribute('data-company-name') || '';
                const rowCompanyAddress = row.getAttribute('data-company-address') || '';
                
                // Get shipping option - need to map display text back to value
                let currentShippingOption = '';
                if (shippingOptionCell && shippingOptionCell.textContent.trim() !== 'N/A') {
                    const shippingText = shippingOptionCell.textContent.trim();
                    // Map display text to value
                    if (shippingText === 'Provide a rate quote before shipping') currentShippingOption = 'rate_quote';
                    else if (shippingText === 'Please ship at cheapest rate') currentShippingOption = 'cheapest_rate';
                    else if (shippingText === 'Client will use their own carrier') currentShippingOption = 'own_carrier';
                    else if (shippingText === 'Client will pickup') currentShippingOption = 'client_pickup';
                    else if (shippingText === 'Yannick will pickup this order') currentShippingOption = 'yannick_pickup';
                    else if (shippingText === 'Ship with DHC\'s courier and add cost to invoice') currentShippingOption = 'dhc_courier';
                }

                // Populate form
                if (customerIdInput) {
                    customerIdInput.value = customerId;
                }
                document.getElementById('customer_name').value = currentName;
                document.getElementById('customer_email').value = currentEmail;
                document.getElementById('customer_phone').value = currentPhone;
                document.getElementById('customer_mobile').value = currentMobile;
                document.getElementById('customer_comment').value = currentComment;
                document.getElementById('customer_shipping_option').value = currentShippingOption;
                if (hasCompanySelect) hasCompanySelect.value = rowHasCompany ? 'true' : 'false';
                if (companyNameInput) companyNameInput.value = rowCompanyName;
                if (companyAddressInput) companyAddressInput.value = rowCompanyAddress;
                toggleCompanyFields();

                // Show form
                document.getElementById('form_title').textContent = 'Edit Customer';
                formRow.classList.remove('d-none');
                addBtn.classList.add('d-none');
                
                // Scroll to form
                formRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        });

        // Delete button handler - simple event delegation
        document.body.addEventListener('click', function(e) {
            // Check if clicked element or parent has delete-customer-btn class
            let deleteBtn = null;
            if (e.target.classList.contains('delete-customer-btn')) {
                deleteBtn = e.target;
            } else if (e.target.closest('.delete-customer-btn')) {
                deleteBtn = e.target.closest('.delete-customer-btn');
            }
            
            if (deleteBtn) {
                e.preventDefault();
                e.stopPropagation();
                
                const customerId = deleteBtn.getAttribute('data-customer-id');
                console.log('Delete clicked for customer:', customerId);
                
                if (!customerId) {
                    console.error('No customer ID found');
                    return;
                }

                if (!confirm('Are you sure you want to delete this customer?')) {
                    return;
                }

                const originalText = deleteBtn.textContent;
                deleteBtn.disabled = true;
                deleteBtn.textContent = 'Deleting...';

                const csrfToken = getCsrfToken();

                fetch('/my/delete_customer', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRF-TOKEN': csrfToken,
                    },
                    body: JSON.stringify({
                        customer_id: parseInt(customerId)
                    }),
                })
                .then(res => {
                    if (!res.ok) {
                        throw new Error(`HTTP error! Status: ${res.status}`);
                    }
                    return res.json();
                })
                .then(data => {
                    if (data.success === false) {
                        alert('Error: ' + (data.error || 'Failed to delete customer'));
                        return;
                    }
                    alert('Customer deleted successfully!');
                    setTimeout(() => {
                        window.location.reload();
                    }, 500);
                })
                .catch(err => {
                    console.error('Error:', err);
                    alert('Failed to delete customer. Please try again.');
                })
                .finally(() => {
                    deleteBtn.disabled = false;
                    deleteBtn.textContent = originalText;
                });
            }
        });

        // Reset form
        function resetForm() {
            if (customerIdInput) {
                customerIdInput.value = '';
            }
            const nameInput = document.getElementById('customer_name');
            const emailInput = document.getElementById('customer_email');
            const phoneInput = document.getElementById('customer_phone');
            const mobileInput = document.getElementById('customer_mobile');
            const commentInput = document.getElementById('customer_comment');
            const shippingOptionInput = document.getElementById('customer_shipping_option');
            
            if (nameInput) nameInput.value = '';
            if (emailInput) emailInput.value = '';
            if (phoneInput) phoneInput.value = '';
            if (mobileInput) mobileInput.value = '';
            if (commentInput) commentInput.value = '';
            if (shippingOptionInput) shippingOptionInput.value = '';
            if (hasCompanySelect) hasCompanySelect.value = 'false';
            if (companyNameInput) companyNameInput.value = '';
            if (companyAddressInput) companyAddressInput.value = '';
            toggleCompanyFields();
            
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save';
            }
        }
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCustomerForm);
    } else {
        initCustomerForm();
    }

})();
