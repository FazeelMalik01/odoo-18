import { _t } from "@web/core/l10n/translation";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    _setValue(val) {
        const { numpadMode } = this.pos;
        let selectedLine = this.currentOrder.get_selected_orderline();
        if (selectedLine) {
            if (numpadMode === "discount_number" && val !== "remove") {
                this.pos.setDiscountpriceFromUI(selectedLine, val);
            }else {
                super._setValue(val);
            }
        }else{
            super._setValue(val);
        }
    }
})