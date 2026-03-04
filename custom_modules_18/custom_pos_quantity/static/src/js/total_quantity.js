import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

// Patch OrderWidget to add getTotalQuantity method
patch(OrderWidget.prototype, {
    getTotalQuantity() {
        if (!this.props.lines || this.props.lines.length === 0) {
            return 0;
        }
        return this.props.lines.reduce((total, line) => {
            const qty = parseFloat(line.qty) || 0;
            return total + qty;
        }, 0);
    },
});

// Patch OrderReceipt to add getTotalQuantity method
patch(OrderReceipt.prototype, {
    getTotalQuantity() {
        if (!this.props.data || !this.props.data.orderlines || this.props.data.orderlines.length === 0) {
            return 0;
        }
        return this.props.data.orderlines.reduce((total, line) => {
            const qty = parseFloat(line.qty) || 0;
            return total + qty;
        }, 0);
    },
});