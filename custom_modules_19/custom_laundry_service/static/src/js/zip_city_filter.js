(function() {
    'use strict';

    function filterCitiesByZipCode() {
        const zipSelect = document.getElementById('zip');
        const citySelect = document.getElementById('city_1');
        
        if (!zipSelect || !citySelect) {
            return;
        }

        // Check if already initialized
        if (zipSelect.dataset.cityFilterInitialized === 'true') {
            return;
        }
        zipSelect.dataset.cityFilterInitialized = 'true';

        function updateCityDropdown() {
            const selectedZip = zipSelect.value;
            const selectedOption = zipSelect.options[zipSelect.selectedIndex];
            
            // Clear existing city options except the first one
            citySelect.innerHTML = '<option value="">Select city...</option>';
            
            if (selectedZip && selectedOption) {
                // Get city names from data attribute
                const cityNames = selectedOption.getAttribute('data-city-names');
                
                if (cityNames) {
                    const cities = cityNames.split(',').filter(city => city.trim() !== '');
                    cities.forEach(function(cityName) {
                        const option = document.createElement('option');
                        option.value = cityName.trim();
                        option.textContent = cityName.trim();
                        citySelect.appendChild(option);
                    });
                }
            }
        }

        // Add event listener for zip code change
        zipSelect.addEventListener('change', updateCityDropdown);
        
        // Also update on page load if zip code is already selected
        if (zipSelect.value) {
            updateCityDropdown();
        }
    }

    // Run when DOM is ready
    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function() {
        filterCitiesByZipCode();

        // Also handle dynamically added elements (for Odoo's dynamic content)
        const observer = new MutationObserver(function(mutations) {
            filterCitiesByZipCode();
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
