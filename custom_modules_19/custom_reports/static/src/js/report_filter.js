/** @odoo-module **/

document.addEventListener('DOMContentLoaded', function() {
    // Function to filter reports based on state
    function filterReports() {
        // Get the current sale order state from the form
        const stateField = document.querySelector('[name="state"]');
        if (!stateField) {
            return;
        }

        let state;
        if (stateField.tagName === 'INPUT' || stateField.tagName === 'SELECT') {
            state = stateField.value;
        } else {
            state = stateField.textContent.trim();
        }

        console.log('Current state:', state);

        // Find all report menu items
        setTimeout(function() {
            const reportItems = document.querySelectorAll('.o_dropdown_menu a, .o-dropdown-menu a');

            reportItems.forEach(item => {
                const text = item.textContent.trim();
                const parentLi = item.closest('li');

                if (!parentLi) return;

                // Show Tax Quotation in draft and sale only
                if (text.includes('Tax Quotation')) {
                    if (state !== 'draft' && state !== 'sale') {
                        parentLi.style.display = 'none';
                    } else {
                        parentLi.style.display = '';
                    }
                }

                // Show Proforma Invoice in draft and sale only
                if (text.includes('Proforma Invoice')) {
                    if (state !== 'draft' && state !== 'sale') {
                        parentLi.style.display = 'none';
                    } else {
                        parentLi.style.display = '';
                    }
                }
            });
        }, 500);
    }

    // Run filter when page loads
    setTimeout(filterReports, 1000);

    // Also run when state changes
    const stateField = document.querySelector('[name="state"]');
    if (stateField) {
        stateField.addEventListener('change', filterReports);
    }

    // Observe DOM changes for dynamic content
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                setTimeout(filterReports, 500);
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});