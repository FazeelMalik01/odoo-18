/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    async updateSelectedOrderline({ buffer, key }) {
        const order = this.pos.get_order();
        const line = order?.get_selected_orderline();
        const cashier = this.pos?.get_cashier?.();

        // Restrict Backspace/Delete only for lines sent to kitchen
        if (
            ["Backspace", "Delete"].includes(key) &&
            line?.isSentToKitchen &&
            cashier?._is_restrict_remove_line
        ) {
            this.env.services.notification.add(
                "You are not allowed to remove this order line.",
                { type: "warning" }
            );
            return; // prevent normal handling
        }

        return await super.updateSelectedOrderline({ buffer, key });
    }
});
