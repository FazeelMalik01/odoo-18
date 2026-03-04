// /** @odoo-module **/
//
// import { PosOrder } from "@point_of_sale/app/models/pos_order";
// import { patch } from "@web/core/utils/patch";
//
//
// patch(PosOrder.prototype, {
//     export_for_printing(baseUrl, headerData) {
//         const lines = [...this.get_orderlines()];
//
//         const groupedObjects = lines.reduce((acc, line) => {
//             const product = line.product_id;
//             const productName = product.display_name || product.name;
//             if (!acc[product.id]) {
//                 acc[product.id] = { product_name: productName, lines: [] };
//             }
//             acc[product.id].lines.push(line);
//             return acc;
//         }, {});
//
//         const groupedOrderlines = Object.values(groupedObjects);
//         const orderlines = super.export_for_printing(...arguments) || {};
//
//         // Always define grouped_by_product
//         orderlines.grouped_by_product = groupedOrderlines.length ? groupedOrderlines : [];
//
//         return orderlines;
//     },
// });
