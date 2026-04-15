/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        this._actionService = useService("action");
    },
    openRentalPos() {
        try {
            localStorage.removeItem("rental_pos_state");
        } catch (_) {
            /* ignore private mode / quota */
        }
        this._actionService.doAction({
            type: "ir.actions.client",
            tag: "rental_pos_page",
            name: "Rental POS",
            context: { rental_pos_fresh_categories: true },
        });
    },
});
