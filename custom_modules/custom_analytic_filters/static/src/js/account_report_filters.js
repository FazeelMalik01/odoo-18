/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AccountReport } from "@account_reports/components/account_report/account_report";

patch(AccountReport.prototype, {
    async setup() {
        if (super.setup) {
            await super.setup();
        }

        // Initialize options safely
        if (!this.options) {
            this.options = {};
        }

        // Loading state + empty data initially
        this.options.purchase_orders = [];
        this.isLoadingPO = true;

        // Artificial delay (e.g., to simulate smooth load)
        setTimeout(async () => {
            await this.loadPurchaseOrders();
        }, 500); // ⏱ 0.5 second delay before fetching
    },

    async loadPurchaseOrders() {
        try {
            const result = await this.orm.call("account.move", "get_purchase_orders", []);
            if (!this.options) this.options = {};

            // Map results to dropdown structure
            this.options.purchase_orders = result.map(po => ({
                id: po.id,
                name: po.name,
                analytic_account_name: po.analytic_account_name,
                selected: false,
            }));

            this.isLoadingPO = false; // ✅ Data is now ready
            this.render();
            console.log("Loaded purchase orders:", result);
        } catch (error) {
            this.isLoadingPO = false;
            console.error("Error loading Purchase Orders:", error);
            this.render();
        }
    },

    selectPurchaseOrder(po) {
        if (!this.options || !this.options.purchase_orders) return;

        this.options.purchase_orders.forEach(p => (p.selected = false));
        po.selected = true;
        this.render();

        // Optionally reload the report based on selection
        this.trigger("reload-report", { purchase_order_id: po.id });
    },
});
