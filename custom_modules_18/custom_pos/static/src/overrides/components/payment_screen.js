///** @odoo-module **/
//
//import { patch } from "@web/core/utils/patch";
//import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
//import { useState } from "@odoo/owl";
//
//patch(PaymentScreen.prototype, {
//    setup() {
//        super.setup();
//        if (!this.state) {
//            this.state = useState({});
//        }
//        this.state.isUsdPayment = this.state.isUsdPayment ?? false;
//
//        // wrap current order and ensure future orders are wrapped too
//        try {
//            this._wrapOrderAddPaymentLine(this.currentOrder);
//            this._patchPosOrderSelectionHandlers();
//        } catch (e) {
//            console.warn("USD patch init error", e);
//        }
//    },
//
//    toggleCurrency() {
//        this.state.isUsdPayment = !this.state.isUsdPayment;
//        this.numberBuffer?.reset?.();
//        this.render();
//    },
//
//    /**
//     * Live conversion while typing:
//     * keep numberBuffer untouched (it holds USD digits),
//     * but set selected payment line amount to converted LBP.
//     */
//updateSelectedPaymentline(amount = false) {
//    const orig = Object.getPrototypeOf(PaymentScreen.prototype).updateSelectedPaymentline;
//    if (orig) {
//        orig.apply(this, arguments);
//    }
//
//    let selectedLine = this.selectedPaymentLine;
//
//    // ⚡ If no line exists, auto-create default (cash) line
//    if (!selectedLine) {
//        const defaultMethod = this.payment_methods_from_config[0];
//        if (defaultMethod) {
//            this.currentOrder.add_paymentline(defaultMethod);
//            selectedLine = this.selectedPaymentLine;
//        }
//    }
//
//    if (!selectedLine) return;
//
//    // determine USD typed value
//    let usdVal;
//    if (amount !== false) {
//        usdVal = amount;
//    } else {
//        const raw = this.numberBuffer?.get();
//        if (raw === null) {
//            usdVal = null;
//        } else if (raw === "") {
//            usdVal = 0;
//        } else {
//            usdVal = this.numberBuffer.getFloat();
//        }
//    }
//
//    if (usdVal === null) return;
//
//    if (this.state.isUsdPayment) {
//        const rate = this.pos?.config?.dual_currency_rate ?? 89500;
//        selectedLine.set_amount(usdVal * rate);
//    } else {
//        if (!isNaN(usdVal)) selectedLine.set_amount(usdVal);
//    }
//},
//
//    /**
//     * Wrap order.add_paymentline but DO NOT change numberBuffer.
//     * Instead call original add_paymentline and then set the newly
//     * created paymentline amount to the converted LBP numeric value.
//     */
//    _wrapOrderAddPaymentLine(order) {
//        if (!order) return;
//        if (order._isAddPaymentlineWrapped) return;
//        order._isAddPaymentlineWrapped = true;
//
//        const self = this;
//        const originalAdd = order.add_paymentline.bind(order);
//
//order.add_paymentline = function (paymentMethod) {
//    // Read USD value from number buffer (do NOT mutate the buffer)
//    let usdEntered = self.numberBuffer?.getFloat?.();
//    const bufferEmpty = !self.numberBuffer || self.numberBuffer.get() === "";
//
//    // Call the original add_paymentline which will create the line
//    const result = originalAdd(paymentMethod);
//
//    try {
//        const newLine = order.payment_ids.at(-1);
//        if (newLine) {
//            const rate = self.pos?.config?.dual_currency_rate ?? 89500;
//
//            // ✅ Preserve default Odoo full amount if buffer was empty
//            if (bufferEmpty) {
//                console.log("[USD] Default full amount preserved:", newLine.amount);
//            } else if (self.state.isUsdPayment) {
//                // USD → convert
//                const converted = usdEntered * rate;
//                newLine.set_amount(converted);
//                console.log("[USD] created paymentline: USD", usdEntered, "→ LBP", converted);
//            } else {
//                newLine.set_amount(usdEntered);
//            }
//        }
//    } catch (e) {
//        console.warn("[USD] post-add conversion failed", e);
//    }
//
//    return result;
//};
//
//
//        // order.add_paymentline = function (paymentMethod) {
//        //     // Read USD value from number buffer (do NOT mutate the buffer)
//        //     let usdEntered = self.numberBuffer?.getFloat?.();
//        //     if (usdEntered == null || isNaN(usdEntered)) {
//        //         usdEntered = 0;
//        //     }
//        //
//        //     // Call the original add_paymentline which will create the line
//        //     const result = originalAdd(paymentMethod);
//        //
//        //     // After it runs, pick the last payment line and set converted amount
//        //     try {
//        //         const newLine = order.payment_ids.at(-1);
//        //         if (newLine) {
//        //             if (self.state.isUsdPayment) {
//        //                 const rate = self.pos?.config?.dual_currency_rate ?? 89500;
//        //                 const converted = usdEntered * rate;
//        //                 newLine.set_amount(converted);
//        //                 console.log("[USD] created paymentline: USD", usdEntered, "→ LBP", converted);
//        //             } else {
//        //                 // if not usd mode, leave as original (or set to usdEntered for safety)
//        //                 newLine.set_amount(usdEntered);
//        //             }
//        //         }
//        //     } catch (e) {
//        //         console.warn("[USD] post-add conversion failed", e);
//        //     }
//        //
//        //     return result;
//        // };
//
//        console.log("[USD] Wrapped order.add_paymentline for order", order.uuid || order.id);
//    },
//
//    _patchPosOrderSelectionHandlers() {
//        try {
//            const pos = this.pos;
//            const self = this;
//            if (!pos) return;
//
//            if (!pos._selectEmptyOrderWrapped && pos.selectEmptyOrder) {
//                pos._selectEmptyOrderWrapped = true;
//                const orig = pos.selectEmptyOrder.bind(pos);
//                pos.selectEmptyOrder = function () {
//                    const res = orig();
//                    self._wrapOrderAddPaymentLine(pos.get_order());
//                    return res;
//                };
//            }
//
//            if (!pos._selectOrderWrapped && pos.selectOrder) {
//                pos._selectOrderWrapped = true;
//                const orig = pos.selectOrder.bind(pos);
//                pos.selectOrder = function (order) {
//                    const res = orig(order);
//                    self._wrapOrderAddPaymentLine(pos.get_order());
//                    return res;
//                };
//            }
//        } catch (e) {
//            console.warn("patch pos order selection handlers failed", e);
//        }
//    },
//});
