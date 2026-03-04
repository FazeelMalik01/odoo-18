/** @odoo-module **/

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { ConnectionLostError } from "@web/core/network/rpc";
import { deduceUrl } from "@point_of_sale/utils";
import { parseFloat } from "@web/views/fields/parsers";

patch(ClosePosPopup.prototype, {
    async confirm() {
        // Call the original confirm method first to close the session
        const result = await super.confirm();
        return result;
    },
    
    async closeSession() {
        // Store session ID before closing (in case it gets cleared)
        const sessionId = this.pos?.session?.id;
        
        // Call parent's closeSession logic up to the point before location.reload()
        this.pos._resetConnectedCashier();
        
        if (this.pos.config.customer_display_type === "proxy") {
            const proxyIP = this.pos.getDisplayDeviceIP();
            fetch(`${deduceUrl(proxyIP)}/hw_proxy/customer_facing_display`, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ params: { action: "close" } }),
            }).catch(() => {});
        }
        
        // If there are orders in the db left unsynced, we try to sync.
        const syncSuccess = await this.pos.push_orders_with_closing_popup();
        if (!syncSuccess) {
            return;
        }
        
        if (this.pos.config.cash_control) {
            const response = await this.pos.data.call(
                "pos.session",
                "post_closing_cash_details",
                [this.pos.session.id],
                {
                    counted_cash: parseFloat(
                        this.state.payments[this.props.default_cash_details.id].counted
                    ),
                }
            );

            if (!response.successful) {
                return this.handleClosingError(response);
            }
        }

        try {
            await this.pos.data.call("pos.session", "update_closing_control_state_session", [
                this.pos.session.id,
                this.state.notes,
            ]);
        } catch (error) {
            if (!error.data && error.data.message !== "This session is already closed.") {
                throw error;
            }
        }

        try {
            const bankPaymentMethodDiffPairs = this.props.non_cash_payment_methods
                .filter((pm) => pm.type == "bank")
                .map((pm) => [pm.id, this.getDifference(pm.id)]);
            const response = await this.pos.data.call(
                "pos.session",
                "close_session_from_ui",
                [this.pos.session.id, bankPaymentMethodDiffPairs],
                {
                    context: {
                        login_number: odoo.login_number,
                    },
                }
            );
            if (!response.successful) {
                return this.handleClosingError(response);
            }
            
            localStorage.removeItem(`pos.session.${odoo.pos_config_id}`);
            
            // Download the sales report AFTER session is closed but BEFORE reload
            try {
                if (typeof this.downloadSalesReport === 'function') {
                    await this.downloadSalesReport();
                } else if (this.report && sessionId) {
                    await this.report.doAction("point_of_sale.sale_details_report", [sessionId]);
                }
            } catch (error) {
                // Silently fail - don't prevent page reload
            }
            
            location.reload();
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                throw error;
            } else {
                await this.handleClosingControlError();
            }
        }
    }
});
