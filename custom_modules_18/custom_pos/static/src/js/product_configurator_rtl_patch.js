/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { 
    BaseProductAttribute,
    RadioProductAttribute,
    PillsProductAttribute,
    SelectProductAttribute,
    ColorProductAttribute,
    MultiProductAttribute,
    ProductConfiguratorPopup 
} from "@point_of_sale/app/store/product_configurator_popup/product_configurator_popup";
import { getTextDirection } from "./rtl_utils";

/**
 * Patch BaseProductAttribute to add RTL/LTR direction detection
 */
patch(BaseProductAttribute.prototype, {
    /**
     * Get text direction for a given text
     * @param {string} text - Text to analyze
     * @returns {string} - 'rtl' or 'ltr'
     */
    getTextDirection(text) {
        return getTextDirection(text);
    },
});

/**
 * Patch ProductConfiguratorPopup to add RTL/LTR support
 */
patch(ProductConfiguratorPopup.prototype, {
    /**
     * Get text direction for attribute name or value
     * @param {string} text - Text to analyze
     * @returns {string} - 'rtl' or 'ltr'
     */
    getTextDirection(text) {
        return getTextDirection(text);
    },
});

console.log("✅ Product Configurator RTL/LTR patch loaded");

