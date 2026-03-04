/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

// 1) Mark the order when user clicks Validate on the Payment screen
patch(PaymentScreen.prototype, {
    async validateOrder(...args) {
        try {
            // flag so ReceiptScreen knows to auto-send via WhatsApp once mounted
            this.currentOrder._whatsapp_send_on_receipt = true;
        } catch (err) {
            // non-blocking
            console.warn("custom_whatsapp: could not set whatsapp flag before validation", err);
        }
        return await super.validateOrder(...args);
    },
});

// 2) When the Receipt screen appears after validation, wait a moment and send
const originalReceiptSetup = ReceiptScreen.prototype.setup;
patch(ReceiptScreen.prototype, {
    setup() {
        // call the original setup to initialize services/state (e.g., this.ui)
        originalReceiptSetup.call(this);

        onMounted(async () => {
            try {
                const shouldSend = this.currentOrder?._whatsapp_send_on_receipt;
                if (
                    shouldSend &&
                    this.pos?.config?.whatsapp_enabled &&
                    typeof this.actionSendReceiptOnWhatsapp === "function" &&
                    this.state?.phone
                ) {
                    // Ensure the receipt is fully rendered before sending
                    await new Promise((resolve) => setTimeout(resolve, 300));
                    await this.actionSendReceiptOnWhatsapp();
                }
            } catch (err) {
                console.warn("custom_whatsapp: failed to invoke WhatsApp after validate", err);
            } finally {
                // Clear the flag to avoid sending again on New Order or revisits
                if (this.currentOrder) {
                    this.currentOrder._whatsapp_send_on_receipt = false;
                }
            }
        });
    },
});
