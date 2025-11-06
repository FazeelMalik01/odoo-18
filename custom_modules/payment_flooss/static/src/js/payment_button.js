/** @odoo-module **/

import paymentButton from '@payment/js/payment_button';

paymentButton.include({

    /**
     * Check if the current payment option is Flooss
     * @private
     * @returns {boolean}
     */
    _isFloossSelected() {
        const selectedRadio = document.querySelector('input[name="o_payment_radio"]:checked');
        return selectedRadio && selectedRadio.dataset.providerCode === 'flooss';
    },

    /**
     * Override to handle Flooss button visibility
     * @override
     */
    start() {
        const result = this._super(...arguments);

        // Listen for radio button changes
        document.addEventListener('change', (event) => {
            if (event.target.name === 'o_payment_radio') {
                this._updateFloossButtons();
            }
        });

        // Initial state
        this._updateFloossButtons();

        return result;
    },

    /**
     * Update Flooss button visibility based on selection
     * @private
     */
    _updateFloossButtons() {
        const container = document.getElementById('o_flooss_button_container');
        const enabledBtn = document.getElementById('o_flooss_enabled_button');
        const disabledBtn = document.getElementById('o_flooss_disabled_button');
        const defaultBtn = document.querySelector('button[name="o_payment_submit_button"]');

        if (this._isFloossSelected()) {
            // Show Flooss buttons, hide default button
            if (container) container.classList.remove('d-none');
            if (enabledBtn) enabledBtn.classList.remove('d-none');
            if (disabledBtn) disabledBtn.classList.add('d-none');
            if (defaultBtn) defaultBtn.classList.add('d-none');
        } else {
            // Hide Flooss buttons, show default button
            if (container) container.classList.add('d-none');
            if (defaultBtn) defaultBtn.classList.remove('d-none');
        }
    }

});