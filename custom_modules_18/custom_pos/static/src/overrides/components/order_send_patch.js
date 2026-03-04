/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

patch(PosStore.prototype, {
    async sendOrderInPreparationUpdateLastChange(order, cancelled = false) {
        if (!order) return;

        if (this.data.network.offline) {
            this.data.network.warningTriggered = false;
            throw new ConnectionLostError();
        }

        // 1️⃣ Original kitchen send logic
        await this.checkPreparationStateAndSentOrderInPreparation(order, cancelled);

        if (!cancelled) {
            order.markAsSentToKitchen();
            console.log("✅ Order sent to kitchen:", order.uid);
        }

        // 2️⃣ Main kitchen receipt print

    },
});
