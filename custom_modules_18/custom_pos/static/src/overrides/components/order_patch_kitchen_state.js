/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(...args) {
        if (super.setup) {
            super.setup(...args);
        }
        // Initialize kitchen flag if not already defined
        this.isSentToKitchen = this.isSentToKitchen ?? false;
    },

    // markAsSentToKitchen() {
    //     this.isSentToKitchen = true;
    //
    //     // Optional: log confirmation for debugging
    //     console.log("✅ Order marked as sent to kitchen:", this.uid);
    // },
    markAsSentToKitchen() {
        // Only mark **existing lines** as sent to kitchen
        this.get_orderlines().forEach(line => {
            line.isSentToKitchen = true;
        });

        console.log("✅ Order lines marked as sent to kitchen:", this.uid);
    },
    isRestrictedOrder() {
        return this.isSentToKitchen === true;
    },
});
