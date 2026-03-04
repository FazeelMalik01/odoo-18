import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    set_discount_price(discount) {
        const parsed_discount =
            typeof discount === "number"
                ? discount
                : isNaN(parseFloat(discount))
                ? 0
                : parseFloat("" + discount);
        const price_unit = this.get_unit_price ? this.get_unit_price() : this.price_unit;
        const qty = this.qty || 1;
        const subtotal_base = price_unit * qty;
    
        let disc_percent = 0;
        if (subtotal_base > 0) {
            disc_percent = (parsed_discount / subtotal_base) * 100;
        }
        disc_percent = Math.min(Math.max(disc_percent, 0), 100);
    
        this.discount = disc_percent;
        console.log("Converted Discount (%):", this.discount);
    
        this.order_id.recomputeOrderData();
        this.setDirty();
    }
})