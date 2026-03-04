/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OrderlineNoteButton } from "@point_of_sale/app/screens/product_screen/control_buttons/customer_note_button/customer_note_button";
import { _t } from "@web/core/l10n/translation";

/**
 * Patch the OrderlineNoteButton to rename "General Note" → "Printed Note"
 */
patch(OrderlineNoteButton.prototype, {
    setup() {
        super.setup?.(); // Keep default setup
    },

    onClick() {
        const label = this.props.label.replace('🖨️', '').trim();
        if (label === _t("Printed Note")) {
            return this.addGeneralNote();
        }
        return this.addLineNotes();
    },


//    onClick() {
//        // ✅ Change logic to use our new “Printed Note”
//        if (this.props.label === _t("Printed Note")) {
//            return this.addGeneralNote();
//        }
//        return this.addLineNotes();
//    },
});