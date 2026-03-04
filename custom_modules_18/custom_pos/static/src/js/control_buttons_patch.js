/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";

patch(ControlButtons.prototype, {
    name: "custom_pos_control_buttons_patch",

    internalNoteLabel(order) {
        if (order) {
//            return _t("Printed Note"); // renamed here
            return `🖨️ ${_t("Printed Note")}`;

        }
        return this.pos.config.module_pos_restaurant ? _t("Kitchen Note") : _t("Internal Note");
    },
});
