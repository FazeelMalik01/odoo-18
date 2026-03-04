/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { parseFullProductName, getTextDirection } from "./rtl_utils";

/**
 * Patch Orderline component to add helper methods for RTL/LTR template rendering
 * 
 * Note: We don't modify getDisplayData() to avoid prop validation issues.
 * Instead, we add helper methods that the template can call directly.
 */
patch(Orderline.prototype, {
    setup() {
        super.setup();
    },
    
    /**
     * Helper to get text direction for any string
     * Can be used in templates: this.getTextDirection(text)
     * @param {string} text - Text to analyze
     * @returns {string} - 'rtl' for Arabic, 'ltr' for others
     */
    getTextDirection(text) {
        return getTextDirection(text);
    },
    
    /**
     * Parse product name for RTL/LTR handling
     * Can be used in templates: this.parseProductName(fullName)
     * @param {string} fullName - Full product name with variants
     * @returns {Object} - Parsed product info with direction
     */
    parseProductName(fullName) {
        return parseFullProductName(fullName);
    },
});

console.log("✅ Orderline RTL/LTR patch loaded");
