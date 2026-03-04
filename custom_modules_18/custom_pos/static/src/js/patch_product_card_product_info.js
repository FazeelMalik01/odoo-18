/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

/** 🧠 Helper: check if current cashier is restricted */
function isRestricted(pos) {
    const cashier = pos?.get_cashier?.();
    return !!cashier?._is_restrict_product_info;
}

/** 1️⃣ ProductCard — hide info icon always, even on selection */
patch(ProductCard.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();

        if (isRestricted(this.pos)) {
            this.props.productInfo = false;
        }
    },

    onClick(ev) {
        if (isRestricted(this.pos)) {
            ev.preventDefault();
            ev.stopPropagation();
            this.trigger("click-product", { product: this.props.product });
            return;
        }
        super.onClick(ev);
    },

    mounted() {
        super.mounted?.();
        this._hideInfoButtonForever();
    },

    patched() {
        super.patched?.();
        this._hideInfoButtonForever();
    },

    _hideInfoButtonForever() {
        if (isRestricted(this.pos)) {
            const infoBtn = this.el.querySelector('.product-info-button, .info-button, .o_product_info_btn');
            if (infoBtn) infoBtn.remove();
        }
    },
});

/** 2️⃣ ProductScreen — override info click to add product instead of popup */
patch(ProductScreen.prototype, {
    async onProductInfoClick(product) {
        if (isRestricted(this.pos)) {
            await this.addProductToOrder(product);  // ✅ Correct call
            return;
        }
        return super.onProductInfoClick?.(product);
    },

    async showProductInfo(product) {
        if (isRestricted(this.pos)) {
            await this.addProductToOrder(product);  // ✅ Correct call
            return;
        }
        return super.showProductInfo?.(product);
    },
});

/** 3️⃣ ProductInfoPopup — just in case popup still opens, close immediately */
patch(ProductInfoPopup.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
        if (isRestricted(this.pos)) {
            // 🔒 Force-close popup
            console.warn("🔒 Product info popup replaced with add_product for restricted cashier");
            this.props.close?.();
        }
    },
});

/** 4️⃣ Orderline — hide info icon in the orderlines too */
patch(Orderline.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    mounted() {
        super.mounted?.();
        this._hideInfoButtonIfRestricted();
    },

    patched() {
        super.patched?.();
        this._hideInfoButtonIfRestricted();
    },

    _hideInfoButtonIfRestricted() {
        if (isRestricted(this.pos)) {
            const btn = this.el.querySelector('.orderline-info-button, .info-button, .product-info-button');
            if (btn) btn.style.display = 'none';
        }
    },
});

console.log("✅ Product info icon fully hidden or replaced with add_product for restricted employees");


// /** @odoo-module **/
//
// import { patch } from "@web/core/utils/patch";
// import { usePos } from "@point_of_sale/app/store/pos_hook";
// import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
// import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
// import { ProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";
// import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
//
// /** 🧠 Helper: check if current cashier is restricted */
// function isRestricted(pos) {
//     const cashier = pos?.get_cashier?.();
//     return !!cashier?._is_restrict_product_info;
// }
//
// /** 1️⃣ ProductCard — hide info icon always, even on selection */
// patch(ProductCard.prototype, {
//     setup() {
//         super.setup();
//         this.pos = usePos();
//
//         // Prevent icon rendering at component level
//         if (isRestricted(this.pos)) {
//             this.props.productInfo = false;
//         }
//     },
//
//     onClick(ev) {
//         if (isRestricted(this.pos)) {
//             ev.preventDefault();
//             ev.stopPropagation();
//             this.trigger("click-product", { product: this.props.product });
//             return;
//         }
//         super.onClick(ev);
//     },
//
//     mounted() {
//         super.mounted?.();
//         this._hideInfoButtonForever();
//     },
//
//     patched() {
//         super.patched?.();
//         this._hideInfoButtonForever();
//     },
//
//     _hideInfoButtonForever() {
//         if (isRestricted(this.pos)) {
//             const infoBtn = this.el.querySelector('.product-info-button, .info-button, .o_product_info_btn');
//             if (infoBtn) infoBtn.remove();
//         }
//     },
// });
//
// /** 2️⃣ ProductScreen — block popup triggers */
// patch(ProductScreen.prototype, {
//     async onProductInfoClick(product) {
//         if (isRestricted(this.pos)) return;
//         return super.onProductInfoClick?.(product);
//     },
//
//     async showProductInfo(product) {
//         if (isRestricted(this.pos)) return;
//         return super.showProductInfo?.(product);
//     },
// });
//
// /** 3️⃣ ProductInfoPopup — auto close if forced open */
// patch(ProductInfoPopup.prototype, {
//     setup() {
//         super.setup();
//         this.pos = usePos();
//         if (isRestricted(this.pos)) {
//             console.warn("🔒 Product info popup auto-closed for restricted cashier");
//             this.props.close?.();
//         }
//     },
// });
//
// /** 4️⃣ Orderline — hide info icon in the orderlines too */
// patch(Orderline.prototype, {
//     setup() {
//         super.setup();
//         this.pos = usePos();
//     },
//
//     mounted() {
//         super.mounted?.();
//         this._hideInfoButtonIfRestricted();
//     },
//
//     patched() {
//         super.patched?.();
//         this._hideInfoButtonIfRestricted();
//     },
//
//     _hideInfoButtonIfRestricted() {
//         if (isRestricted(this.pos)) {
//             const btn = this.el.querySelector('.orderline-info-button, .info-button, .product-info-button');
//             if (btn) btn.style.display = 'none';
//         }
//     },
// });
//
// console.log("✅ Product info icon fully hidden everywhere (even on selected product)");
