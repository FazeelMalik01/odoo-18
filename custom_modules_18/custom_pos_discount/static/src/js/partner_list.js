import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { PosStore } from "@point_of_sale/app/store/pos_store";

// Patch PartnerList to detect phone numbers in search and pass to editPartner
patch(PartnerList.prototype, {
    async editPartner(p = false) {
        // Check if search query exists and is a phone number
        let phoneNumber = null;
        if (!p && this.state.query) {
            // Clean the query to check if it's a phone number
            const cleanedQuery = this.state.query.replace(/[+\s()-]/g, "");
            // Check if it's a numeric string (phone number) - minimum 3 digits to avoid matching very short numbers
            if (/^[0-9]+$/.test(cleanedQuery) && cleanedQuery.length >= 3) {
                phoneNumber = this.state.query.trim();
            }
        }
        
        // Store phone number in POS store temporarily if found
        if (phoneNumber) {
            this.pos._tempPhoneNumber = phoneNumber;
        } else {
            this.pos._tempPhoneNumber = null;
        }
        
        const partner = await super.editPartner(p);
        
        // Clear temporary phone number after use
        if (this.pos._tempPhoneNumber) {
            this.pos._tempPhoneNumber = null;
        }
        
        return partner;
    },
});

// Patch PosStore to include phone number in context when creating new partner
patch(PosStore.prototype, {
    editPartnerContext(partner) {
        const context = super.editPartnerContext(partner);
        
        // If we have a temporary phone number (set when creating new partner), add it to context
        if (this._tempPhoneNumber) {
            context.default_mobile = this._tempPhoneNumber;
        }
        
        return context;
    },
});

