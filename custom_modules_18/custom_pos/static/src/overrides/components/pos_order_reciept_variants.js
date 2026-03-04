// /** @odoo-module **/
/** @odoo-module **/

/** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
//
// patch(OrderWidget.prototype, {
//     /**
//      * Compute lines grouped by product and mark where to show variant title.
//      */
// get groupedLines() {
//     const seen = new Set();
//     return (this.props.lines || []).map(line => {
//         const productId = line.product?.id || line.id;
//         const isTitle = !seen.has(productId);
//         if (isTitle) seen.add(productId);
//         return {
//             line,
//             isTitle,
//             title: line.product?.display_name || line.productName || "",
//         };
//     });
// }
// ,
// });

//
// import { PosOrder } from "@point_of_sale/app/models/pos_order";
// import { patch } from "@web/core/utils/patch";
//
// patch(PosOrder.prototype, {
//     export_for_printing(baseUrl, headerData) {
//         const lines = [...this.get_orderlines()];
//
//         // Group by Product Template
//         const groupedObjects = lines.reduce((acc, line) => {
//             const product = line.get_product();
//             if (!product) return acc;
//
//             const productTemplateId = product.product_tmpl_id?.id || product.id;
//             const productTemplateName = product.product_tmpl_id?.name || product.display_name || product.name;
//
//             if (!acc[productTemplateId]) {
//                 acc[productTemplateId] = {
//                     product_name: productTemplateName,
//                     lines: [],
//                 };
//             }
//
//             // Map all necessary fields for Orderline
//             acc[productTemplateId].lines.push({
//                 ...line, // keep all original fields
//                 productName: line.full_product_name || product.display_name || product.name,
//                 qty: line.get_quantity_str_with_unit ? line.get_quantity_str_with_unit() : line.qty,
//                 unitPrice: line.price_unit,
//                 price: line.price_total,
//                 unit: line.product_id?.uom_id?.name || '',
//                 discount: line.get_discount ? line.get_discount() : 0,
//                 price_without_discount: line.get_price_without_discount ? line.get_price_without_discount() : line.price_total,
//                 customerNote: line.customerNote || '',
//                 internalNote: line.internalNote || '',
//                 packLotLines: line.packLotLines || [],
//                 taxGroupLabels: line.taxGroupLabels || '',
//                 oldUnitPrice: line.oldUnitPrice || null,
//             });
//
//             return acc;
//         }, {});
//
//         const result = Object.values(groupedObjects);
//         const orderlines = super.export_for_printing(...arguments);
//
//         return {
//             ...orderlines,
//             orderlines: result,
//         };
//     },
// });
