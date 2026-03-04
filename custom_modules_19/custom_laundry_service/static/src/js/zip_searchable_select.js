(function() {
    'use strict';

    function initializeZipSearchableSelect() {
        // Find all zip select fields (there might be multiple forms on the page)
        const zipSelects = document.querySelectorAll('select#zip[style*="display: none"]');
        
        zipSelects.forEach(function(zipSelect) {
            // Check if already initialized
            if (zipSelect.dataset.searchInitialized === 'true') {
                return;
            }
            zipSelect.dataset.searchInitialized = 'true';

            // Find the corresponding search input and dropdown
            const container = zipSelect.parentElement;
            if (!container) return;
            
            const zipSearchInput = container.querySelector('input#zip_search');
            const zipDropdown = container.querySelector('#zip_dropdown');
            
            if (!zipSearchInput || !zipDropdown) {
                return;
            }
            
            initializeSingleSelect(zipSearchInput, zipSelect, zipDropdown);
        });
    }

    function initializeSingleSelect(zipSearchInput, zipSelect, zipDropdown) {

        // Populate dropdown with options from select
        function populateDropdown(filterText = '') {
            zipDropdown.innerHTML = '';
            const filter = filterText.toLowerCase().trim();
            let hasVisibleOptions = false;

            for (let i = 0; i < zipSelect.options.length; i++) {
                const option = zipSelect.options[i];
                const optionText = option.textContent.toLowerCase();
                
                // Show all options if filter is empty, otherwise filter
                if (!filter || optionText.includes(filter)) {
                    const dropdownItem = document.createElement('div');
                    dropdownItem.className = 'px-3 py-2 cursor-pointer zip-option';
                    dropdownItem.style.cursor = 'pointer';
                    dropdownItem.textContent = option.textContent;
                    dropdownItem.dataset.value = option.value;
                    dropdownItem.dataset.cityIds = option.getAttribute('data-city-ids') || '';
                    dropdownItem.dataset.cityNames = option.getAttribute('data-city-names') || '';
                    
                    // Highlight on hover
                    dropdownItem.addEventListener('mouseenter', function() {
                        this.style.backgroundColor = '#f8f9fa';
                    });
                    dropdownItem.addEventListener('mouseleave', function() {
                        this.style.backgroundColor = '';
                    });
                    
                    // Select option on click
                    dropdownItem.addEventListener('click', function() {
                        zipSelect.value = this.dataset.value;
                        zipSearchInput.value = this.textContent.trim();
                        zipDropdown.style.display = 'none';
                        
                        // Trigger change event on select for city filtering
                        zipSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    });
                    
                    zipDropdown.appendChild(dropdownItem);
                    hasVisibleOptions = true;
                }
            }

            // Show dropdown if there are visible options
            if (hasVisibleOptions && zipSearchInput === document.activeElement) {
                zipDropdown.style.display = 'block';
            }
        }

        // Show dropdown on focus
        zipSearchInput.addEventListener('focus', function() {
            populateDropdown(this.value);
        });

        // Filter options as user types
        zipSearchInput.addEventListener('input', function() {
            populateDropdown(this.value);
        });

        // Hide dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!zipSearchInput.contains(e.target) && !zipDropdown.contains(e.target)) {
                zipDropdown.style.display = 'none';
            }
        });

        // Set initial value if zip is already selected
        function setInitialValue() {
            if (zipSelect.value) {
                const selectedOption = zipSelect.options[zipSelect.selectedIndex];
                if (selectedOption && selectedOption.value) {
                    zipSearchInput.value = selectedOption.textContent.trim();
                }
            }
        }
        setInitialValue();

        // Sync search input with select value changes (if changed programmatically)
        zipSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption && selectedOption.value) {
                zipSearchInput.value = selectedOption.textContent.trim();
            } else {
                zipSearchInput.value = '';
            }
            zipDropdown.style.display = 'none';
        });

        // Ensure select value is set on form submit
        zipSearchInput.addEventListener('blur', function() {
            // If the input value matches an option, set it
            const inputValue = this.value.trim();
            for (let i = 0; i < zipSelect.options.length; i++) {
                if (zipSelect.options[i].textContent.trim() === inputValue) {
                    zipSelect.value = zipSelect.options[i].value;
                    zipSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    break;
                }
            }
        });
    }
    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function() {
        initializeZipSearchableSelect();

        // Also handle dynamically added elements (for Odoo's dynamic content)
        const observer = new MutationObserver(function(mutations) {
            initializeZipSearchableSelect();
        });

        // Observe the document body for changes
        if (document.body) {
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    });
})();
