/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(ControlButtons.prototype, {
    async onClickAddCustomerNote() {
        const order = this.pos.get_order();
        const payload = await makeAwaitable(this.dialog, TextInputPopup, {
            title: _t("Add General Note"),
            rows: 4,
            startingValue: order.custom_note || "",
        });

        if (typeof payload === "string") {
            order.custom_note = payload;
            this.notification.add(_t("Note added successfully!"));
        }
    },
});
