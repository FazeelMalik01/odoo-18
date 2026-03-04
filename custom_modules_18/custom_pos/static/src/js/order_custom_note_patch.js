///** @odoo-module **/
//
//import { PosOrder } from "@point_of_sale/app/models/pos_order";
//import { patch } from "@web/core/utils/patch";
//
//patch(PosOrder.prototype, {
//    setup() {
//        super.setup(...arguments);
//        this.custom_note = this.custom_note || "";
//    },
//
//    export_as_JSON() {
//        const json = super.export_as_JSON(...arguments);
//        json.custom_note = this.custom_note || "";
//        json.total_with_tax = this.get_total_with_tax?.() || 0;
//        json.total_paid = this.get_total_paid?.() || 0;
//        json.change = this.get_change?.() || 0;
//        return json;
//    },
//
//    init_from_JSON(json) {
//        super.init_from_JSON(...arguments);
//        this.custom_note = json.custom_note || "";
//        this._total_with_tax = json.total_with_tax || 0;
//        this._total_paid = json.total_paid || 0;
//        this._change = json.change || 0;
//    },
//
//    export_for_printing() {
//        const data = super.export_for_printing(...arguments);
//        data.custom_note = this.custom_note || "";
//
//        try {
//            // Safely parse all values as numbers
//            const order_total_lbp = Number(this._total_with_tax || this.get_total_with_tax?.() || 0);
//            const total_paid_lbp = Number(this._total_paid || this.get_total_paid?.() || 0);
//            const change_lbp = Number(this._change || this.get_change?.() || 0);
//
//            // Safe fallback rate
//            const lbp_rate = Number(this.pos?.config?.dual_currency_rate || 89500);
//            const rate = lbp_rate > 0 ? lbp_rate : 89500;
//
//            // Prevent divide-by-zero and NaN
//            const total_usd = rate ? order_total_lbp / rate : 0;
//            const paid_usd = rate ? total_paid_lbp / rate : 0;
//            const change_usd = rate ? change_lbp / rate : 0;
//
//            // Safe formatter
//            const format = this.pos?.format_currency_no_symbol
//                ? (v) => this.pos.format_currency_no_symbol(Number(v || 0))
//                : (v) => Number(v || 0).toFixed(2);
//
//            data.total_lbp_display = format(order_total_lbp);
//            data.total_usd_display = format(total_usd);
//            data.paid_lbp_display = format(total_paid_lbp);
//            data.paid_usd_display = format(paid_usd);
//            data.change_lbp_display = format(change_lbp);
//            data.change_usd_display = format(change_usd);
//            data.order_change = this.get_change?.() || this._change || 0;
//
//
//            console.log(
//                "💰 Dual currency computed:",
//                { order_total_lbp, total_paid_lbp, change_lbp, rate, total_usd, paid_usd, change_usd }
//            );
//        } catch (err) {
//            console.error("Dual currency calculation failed:", err);
//        }
//
//        return data;
//    },
//});
