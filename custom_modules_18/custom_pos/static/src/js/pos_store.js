import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {

    async onDeleteOrder(order) {
    	if(this.get_cashier()._is_restrict_cancel_order){
    		this.dialog.add(AlertDialog, {
                title: _t("Access Error"),
                body: _t("You don't have access to cancel or delate the order. Please contact your manager."),
            });
    		return;
    	}
    	return super.onDeleteOrder(...arguments);
    },
});