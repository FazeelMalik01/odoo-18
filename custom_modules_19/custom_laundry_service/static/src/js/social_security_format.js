(function() {
    'use strict';

    // Format Social Security Number: XXX.XXXX.XXXX.XX
    function formatSocialSecurity(input) {
        if (!input) return;
        
        // Get cursor position before formatting
        const cursorPos = input.selectionStart || 0;
        const oldValue = input.value || '';
        
        // Remove all non-digit characters
        let value = oldValue.replace(/\D/g, '');
        
        // Limit to 13 digits (XXX.XXXX.XXXX.XX = 3+4+4+2 = 13 digits)
        if (value.length > 13) {
            value = value.substring(0, 13);
        }
        
        // Format: XXX.XXXX.XXXX.XX
        let formatted = '';
        if (value.length > 0) {
            formatted = value.substring(0, 3);
        }
        if (value.length > 3) {
            formatted += '.' + value.substring(3, 7);
        }
        if (value.length > 7) {
            formatted += '.' + value.substring(7, 11);
        }
        if (value.length > 11) {
            formatted += '.' + value.substring(11, 13);
        }
        
        // Set the formatted value
        input.value = formatted;
        
        // Restore cursor position (adjust for added dots)
        const beforeCursor = oldValue.substring(0, cursorPos);
        const digitsBeforeCursor = beforeCursor.replace(/\D/g, '').length;
        
        // Calculate new cursor position by counting digits and dots
        let newCursorPos = 0;
        let digitCount = 0;
        for (let i = 0; i < formatted.length; i++) {
            if (formatted[i] === '.') {
                newCursorPos++;
            } else {
                digitCount++;
                if (digitCount <= digitsBeforeCursor) {
                    newCursorPos++;
                } else {
                    break;
                }
            }
        }
        
        // Set cursor position
        setTimeout(function() {
            input.setSelectionRange(newCursorPos, newCursorPos);
        }, 0);
    }

    // Handle input event for real-time formatting
    function handleSocialSecurityInput(e) {
        const input = e.target;
        if (input && (input.id === 'social_security_no' || input.name === 'social_security_no')) {
            formatSocialSecurity(input);
        }
    }

    // Handle paste event
    function handleSocialSecurityPaste(e) {
        const input = e.target;
        if (input && (input.id === 'social_security_no' || input.name === 'social_security_no')) {
            e.preventDefault();
            const pastedData = (e.clipboardData || window.clipboardData).getData('text');
            const digitsOnly = pastedData.replace(/\D/g, '').substring(0, 13);
            input.value = digitsOnly;
            formatSocialSecurity(input);
        }
    }

    // Initialize for existing elements
    function initSocialSecurityFormatting() {
        const ssnInputs = document.querySelectorAll('#social_security_no, input[name="social_security_no"]');
        ssnInputs.forEach(function(input) {
            if (!input.dataset.formatted) {
                input.dataset.formatted = 'true';
                // Format existing value if any
                if (input.value) {
                    formatSocialSecurity(input);
                }
                // Add event listeners
                input.addEventListener('input', handleSocialSecurityInput, false);
                input.addEventListener('paste', handleSocialSecurityPaste, false);
            }
        });
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
        initSocialSecurityFormatting();

        // Also handle dynamically added elements (for Odoo's dynamic content)
        const observer = new MutationObserver(function(mutations) {
            initSocialSecurityFormatting();
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

