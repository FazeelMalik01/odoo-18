/** @odoo-module **/

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {
    async confirm() {
        try {
            // Download the sales report before closing the session
            await this.downloadSalesReport();
        } catch (error) {
            // Log the error but don't prevent closing the session
            console.warn("Failed to download sales report:", error);
        }
        
        // Call the original confirm method
        return super.confirm();
    }
});
