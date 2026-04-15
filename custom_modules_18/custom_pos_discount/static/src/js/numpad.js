// /** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { PosStore } from "@point_of_sale/app/store/pos_store";

// console.log("✅ numpad_patch.js loaded successfully");

// // Intercept +/- button click at DOM level
// document.addEventListener("click", (event) => {
//     const btn = event.target.closest('button[value="+/-"]');
//     if (!btn) return;

//     // Check if price button is currently active
//     const priceBtn = document.querySelector('button.numpad-price');
//     console.log("🔑 +/- clicked | priceBtn active:", priceBtn?.classList);

//     if (priceBtn && priceBtn.classList.contains("active")) {
//         console.log("🚫 Blocked +/- in price mode");
//         event.stopImmediatePropagation();
//         event.preventDefault();
//     }
// }, true); // true = capture phase, fires before Odoo's handler

/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

console.log("✅ numpad_patch.js loaded successfully");

// Intercept +/- button click at DOM level
document.addEventListener("click", (event) => {
    const btn = event.target.closest('button[value="+/-"]');
    if (!btn) return;

    const priceBtn = document.querySelector('button.numpad-price');
    console.log("🔑 +/- clicked | priceBtn active:", priceBtn?.classList);

    if (priceBtn && priceBtn.classList.contains("active")) {
        console.log("🚫 Blocked +/- in price mode");
        event.stopImmediatePropagation();
        event.preventDefault();
    }
}, true);

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const product = vals.product_id;
        if (product?.type === "combo") {
            const combos = product.combo_ids || [];
            const allSingle = combos.length > 0 && combos.every(
                (combo) => (combo.combo_line_ids?.length || 0) <= 1
            );
            if (allSingle) {
                configure = true;
            }
        }
        return super.addLineToCurrentOrder(vals, opts, configure);
    },
});