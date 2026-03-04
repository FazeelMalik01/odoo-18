/** @odoo-module **/

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    /**
     * Override goToOrders to filter by partner ID instead of partner name
     * This ensures that when clicking "All Orders" for a customer,
     * only orders for that specific customer (by ID) are shown,
     * even if there are multiple customers with the same name.
     */
    goToOrders(partner) {
        this.clickPartner(this.props.partner);
        const partnerHasActiveOrders = this.pos
            .get_open_orders()
            .some((order) => order.partner?.id === partner.id);
        const stateOverride = {
            search: {
                fieldName: "PARTNER", // Use PARTNER field to show name in search bar
                searchTerm: partner.name || partner.complete_name || "", // Show customer name in search field
            },
            filter: partnerHasActiveOrders ? "" : "SYNCED",
            partnerId: partner.id, // Store partner ID for actual filtering (not shown in search)
        };
        this.pos.showScreen("TicketScreen", { stateOverride });
    },
});
