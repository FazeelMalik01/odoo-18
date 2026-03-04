/** @odoo-module **/
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import {
    BACKSPACE,
    ZERO,
    getButtons,
} from "@point_of_sale/app/generic_components/numpad/numpad";

patch(ProductScreen.prototype, {
    getNumpadButtons() {
        const colorClassMap = {
            [this.env.services.localization.decimalPoint]: "o_colorlist_item_color_transparent_6",
            Backspace: "o_colorlist_item_color_transparent_1",
            "-": "o_colorlist_item_color_transparent_3",
        };

        const buttons = getButtons([{ value: "-", text: "+/-", disabled: true }, ZERO, BACKSPACE], [
            { value: "quantity", text: _t("Qty") },
            { value: "discount", text: _t("Discount %"), disabled: !this.pos.config.manual_discount },
            { value: "discount_number", text: _t("Discount Amount"), disabled: !this.pos.config.manual_discount },
            {
                value: "price",
                text: _t("Price"),
                disabled: !this.pos.cashierHasPriceControlRights(),
            },
        ]).map((button) => ({
            ...button,
            class: `
                ${colorClassMap[button.value] || ""}
                ${this.pos.numpadMode === button.value ? "active" : ""}
                ${button.value === "quantity" ? "numpad-qty rounded-0 rounded-top mb-0" : ""}
                ${button.value === "price" ? "numpad-price rounded-0 rounded-bottom mt-0" : ""}
                ${
                    button.value === "discount"
                        ? "numpad-discount my-0 rounded-0 border-top border-bottom"
                        : ""
                }
                ${
                    button.value === "discount_number"
                        ? "numpad-discount my-0 rounded-0 border-top border-bottom"
                        : ""
                }
            `,
        }));

        // 🧠 Add restriction for Backspace dynamically
        const cashier = this.pos.get_cashier?.();
        // if (cashier && cashier._is_restrict_remove_line) {
        //     buttons.forEach((b) => {
        //         if (b.value === "Backspace") {
        //             b.disabled = true;
        //         }
        //     });
        // }

        return buttons;
    },

    // onNumpadClick(buttonValue) {
    //     if (["quantity", "discount", "price", "discount_number"].includes(buttonValue)) {
    //         this.numberBuffer.capture();
    //         this.numberBuffer.reset();
    //         this.pos.numpadMode = buttonValue;
    //         return;
    //     }
    //     this.numberBuffer.sendKey(buttonValue);
    // },
onNumpadClick(buttonValue) {
        // const line = this.currentOrder.get_selected_orderline();
        const line = this.currentOrder?.get_selected_orderline?.();
        const cashier = this.pos.get_cashier?.();
        const qty = line ? Number(line.get_quantity?.() || line.quantity || 0) : 0;
        const isRestrictedOrder = this.currentOrder?.isSentToKitchen;
        const isRestrictedLine = line?.isSentToKitchen;
// Handle Backspace restriction
        if (isRestrictedLine && buttonValue === "Backspace" && line && qty <= 1 && cashier?._is_restrict_remove_line) {
            this.env.services.notification.add(
                "You are not allowed to remove this order line.",
                { type: "warning" }
            );
            return; // prevent removing the line
        }

        // Restrict reducing quantity below 1 using number buffer
        if (buttonValue === "-" && line && qty <= 1 && cashier?._is_restrict_remove_line) {
            this.env.services.notification.add(
                "You cannot reduce quantity below 1 for this order line.",
                { type: "warning" }
            );
            return; // prevent decreasing qty
        }

        // Handle mode buttons
        if (["quantity", "discount", "price", "discount_number"].includes(buttonValue)) {
            this.numberBuffer.capture();
            this.numberBuffer.reset();
            this.pos.numpadMode = buttonValue;
            return;
        }

        // Default: send key to numberBuffer
        this.numberBuffer.sendKey(buttonValue);
    },
   onKeyDown(ev) {
        const line = this.currentOrder?.get_selected_orderline?.();
        const cashier = this.pos.get_cashier?.();
        const qty = line ? Number(line.get_quantity?.() || line.quantity || 0) : 0;
        const isRestrictedOrder = this.currentOrder?.isSentToKitchen;

        // Detect restricted actions via keyboard
        const restrictedKeys = ["Backspace", "Delete", "Minus", "-"];

        // if (
        //     isRestrictedOrder &&
        //     line &&
        //     qty <= 1 &&
        //     cashier?._is_restrict_remove_line &&
        //     restrictedKeys.includes(ev.key)
        // ) {
            this.env.services.notification.add(
                "You are not allowed to remove or reduce this order line.",
                { type: "warning" }
            );
            ev.preventDefault();
            ev.stopPropagation();
            return;
        // }

        // otherwise, continue normal keyboard handling
        super.onKeyDown(ev);
    },

});