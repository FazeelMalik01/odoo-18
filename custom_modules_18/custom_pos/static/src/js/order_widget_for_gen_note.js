// /** @odoo-module **/
// import { patch } from "@web/core/utils/patch";
// import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
//
// patch(Orderline.prototype, {
//     get customerNote() {
//         // Only show for a special "note line" or the last line
//         const order = this.props.line.order;
//         return order?.custom_note || "";
//     },
// });
