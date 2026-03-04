// /** @odoo-module **/
//
// import { Order } from "@point_of_sale/apps/models";
//
// const OriginalAddProduct = Order.prototype.add_product;
//
// Order.prototype.add_product = function(product, options) {
//     const line = OriginalAddProduct.call(this, product, options);
//
//     // If this product has variants
//     if (product.variants && product.variants.length > 0) {
//         line.isVariantGroup = true;        // mark as parent line
//         line.variants = product.variants.map(v => ({
//             productName: v.display_name,
//             qty: v.qty || 1,
//             unitPrice: v.price || 0,
//             discount: v.discount || 0,
//         }));
//     } else {
//         line.isVariantGroup = false;
//         line.variants = [];
//     }
//
//     return line;
// };
