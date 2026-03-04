/** @odoo-module */

import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup(vals) {
        super.setup(...arguments);
        // Initialize card_no from vals if provided
        this.card_no = vals.card_no || '';
    },

    /**
     * Set the card number (last 4 digits)
     */
    set_card_no(value) {
        this.card_no = value || '';
    },

    /**
     * Get the card number
     */
    get_card_no() {
        return this.card_no || '';
    },

    /**
     * Override export_for_printing to include card_no
     */
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.card_no = this.card_no || '';
        return result;
    },
});


