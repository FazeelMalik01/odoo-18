/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    setup(...args) {
        if (super.setup) {
            super.setup(...args);
        }
        // Initialize flag for new lines
        this.isSentToKitchen = this.isSentToKitchen ?? false;
    }
});
