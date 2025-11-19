odoo.define('custom_gatekeeper_security.service_request', function (require) {
    "use strict";

    const publicWidget = require('web.public.widget');

    publicWidget.registry.ServiceRequestForm = publicWidget.Widget.extend({
        selector: '.o_portal_wrap form',
        events: {
            'change input[name="service_type_other"]': '_onToggleOtherDetails',
            'submit': '_onSubmitForm',
        },

        /**
         * @override
         */
        start: function () {
            this.$otherDetails = this.$('input[name="service_type_other_details"]');
            this.$otherCheckbox = this.$('input[name="service_type_other"]');
            this._onToggleOtherDetails();
            return this._super.apply(this, arguments);
        },

        /**
         * Show/hide the "Other service details" input depending on checkbox
         */
        _onToggleOtherDetails: function () {
            if (this.$otherCheckbox.is(':checked')) {
                this.$otherDetails.prop('disabled', false);
                this.$otherDetails.closest('.form-check, .mb-3').show();
            } else {
                this.$otherDetails.prop('disabled', true).val('');
                this.$otherDetails.closest('.form-check, .mb-3').hide();
            }
        },

        /**
         * Optional: Client-side validation before submitting
         */
        _onSubmitForm: function (ev) {
            const requiredFields = ['service_address', 'city', 'zip', 'primary_phone', 'email'];
            let valid = true;

            requiredFields.forEach(function (name) {
                const $field = ev.currentTarget.querySelector(`[name="${name}"]`);
                if ($field && !$field.value.trim()) {
                    valid = false;
                    $field.classList.add('is-invalid');
                } else if ($field) {
                    $field.classList.remove('is-invalid');
                }
            });

            if (!valid) {
                ev.preventDefault();
                alert("Please fill all required fields before submitting the form.");
            }
        },
    });
});
