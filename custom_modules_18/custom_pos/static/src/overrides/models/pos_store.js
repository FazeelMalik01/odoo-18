import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


patch(PosStore.prototype, {
    async setDiscountpriceFromUI(line, val){
        line.set_discount_price(val);
    },
    getReceiptHeaderData() {
        const res = super.getReceiptHeaderData(...arguments)
        res["partner"] = this.selectedOrder.partner_id
        res["cashier"] =  _t("Served by %s", this.config.name)
        return res
    },
    // async pay() {
    //     const currentOrderPOS = this.get_order();
    //     if (!currentOrderPOS.get_partner()) {
    //         this.dialog.add(AlertDialog, {
    //             title: _t("Customer is Required"),
    //             body: _t("Customer is required to proceed with the order!"),
    //         });
    //         return;
    //     }
    //     await super.pay(...arguments);
    // },
})