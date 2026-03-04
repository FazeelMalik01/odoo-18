/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { 
    MultiProductAttribute,
    ProductConfiguratorPopup,
} from "@point_of_sale/app/store/product_configurator_popup/product_configurator_popup";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosStore } from "@point_of_sale/app/store/pos_store";

// Global variable to temporarily hold selection order between configurator and orderline creation
let _pendingSelectionOrder = null;

// Global counter to track the order in which different attributes are interacted with
let _globalInteractionCounter = 0;

/**
 * Patch MultiProductAttribute to track the order of selection
 */
patch(MultiProductAttribute.prototype, {
    setup() {
        super.setup();
        // Track selection order within this attribute
        this.selectionOrderState = useState({ order: [] });
        // Track when this attribute was first interacted with (for cross-attribute ordering)
        this._firstInteractionOrder = null;
    },
    
    /**
     * Called when checkbox is clicked - track the order
     * @param {number} valueId - The ID of the value being toggled
     */
    trackSelection(valueId) {
        const currentOrder = this.selectionOrderState.order;
        const index = currentOrder.indexOf(valueId);
        
        if (index === -1) {
            // Not in list - add it (will be selected)
            this.selectionOrderState.order = [...currentOrder, valueId];
            
            // Track first interaction time for this attribute
            if (this._firstInteractionOrder === null) {
                _globalInteractionCounter++;
                this._firstInteractionOrder = _globalInteractionCounter;
            }
        } else {
            // Already in list - remove it (will be deselected)
            this.selectionOrderState.order = currentOrder.filter(id => id !== valueId);
            
            // If all items deselected, reset the interaction order
            if (this.selectionOrderState.order.length === 0) {
                this._firstInteractionOrder = null;
            }
        }
    },
    
    /**
     * Override getValue to return values in selection order
     */
    getValue() {
        // Get selected values from the actual state
        const selectedValues = this.values.filter((val) => this.state.attribute_value_ids[val.id]);
        
        // Sort by selection order
        const selectionOrder = this.selectionOrderState?.order || [];
        if (selectionOrder.length > 0) {
            selectedValues.sort((a, b) => {
                const orderA = selectionOrder.indexOf(a.id);
                const orderB = selectionOrder.indexOf(b.id);
                if (orderA === -1 && orderB === -1) return 0;
                if (orderA === -1) return 1;
                if (orderB === -1) return -1;
                return orderA - orderB;
            });
        }

        const extra = selectedValues.reduce((acc, val) => acc + val.price_extra, 0);
        const valueIds = selectedValues.map((val) => val.id);
        const value = selectedValues
            .map((val) => {
                if (val.is_custom && this.state.custom_value) {
                    return `${val.name}: ${this.state.custom_value}`;
                }
                return val.name;
            })
            .join(", ");
        const hasCustom = selectedValues.some((val) => val.is_custom);

        return {
            value,
            valueIds,
            custom_value: this.state.custom_value,
            extra,
            hasCustom,
        };
    },
});

/**
 * Patch ProductConfiguratorPopup to pass selection order in payload
 * Orders attributes by when they were first interacted with
 */
patch(ProductConfiguratorPopup.prototype, {
    setup() {
        super.setup();
        // Reset global counter when popup opens
        _globalInteractionCounter = 0;
    },
    
    computePayload() {
        const attribute_custom_values = [];
        let attribute_value_ids = [];
        var price_extra = 0.0;
        
        // Collect all multi-select attributes with their interaction order
        const multiSelectAttrs = [];
        const otherAttrs = [];
        
        this.state.payload.forEach((attribute_component) => {
            const { valueIds, extra, custom_value, hasCustom } = attribute_component.getValue();
            
            // Check if this is a multi-select with tracked order
            if (attribute_component.selectionOrderState?.order?.length > 0) {
                multiSelectAttrs.push({
                    component: attribute_component,
                    valueIds: valueIds,
                    extra: extra,
                    custom_value: custom_value,
                    hasCustom: hasCustom,
                    interactionOrder: attribute_component._firstInteractionOrder || Infinity
                });
            } else {
                // Non-multi-select or no selections tracked
                otherAttrs.push({
                    component: attribute_component,
                    valueIds: valueIds,
                    extra: extra,
                    custom_value: custom_value,
                    hasCustom: hasCustom
                });
            }
        });
        
        // Sort multi-select attributes by their first interaction order
        multiSelectAttrs.sort((a, b) => a.interactionOrder - b.interactionOrder);
        
        // Build the final selection order: other attrs first (in original order), 
        // then multi-selects in interaction order
        let finalSelectionOrder = [];
        
        // Process other (non-multi-select) attributes first
        otherAttrs.forEach(attr => {
            attribute_value_ids.push(attr.valueIds);
            if (attr.hasCustom) {
                attribute_custom_values[attr.valueIds[0]] = attr.custom_value;
            }
            const attrRecord = this.pos.data.models["product.template.attribute.value"].get(attr.valueIds[0]);
            if (attrRecord && attrRecord.attribute_id.create_variant !== "always") {
                price_extra += attr.extra;
            }
        });
        
        // Process multi-select attributes in interaction order
        multiSelectAttrs.forEach(attr => {
            attribute_value_ids.push(attr.valueIds);
            // Add to selection order
            attr.valueIds.forEach(id => {
                if (!finalSelectionOrder.includes(id)) {
                    finalSelectionOrder.push(id);
                }
            });
            if (attr.hasCustom) {
                attribute_custom_values[attr.valueIds[0]] = attr.custom_value;
            }
            const attrRecord = this.pos.data.models["product.template.attribute.value"].get(attr.valueIds[0]);
            if (attrRecord && attrRecord.attribute_id.create_variant !== "always") {
                price_extra += attr.extra;
            }
        });

        attribute_value_ids = attribute_value_ids.flat();
        
        // Store in global variable for the orderline creation to pick up
        _pendingSelectionOrder = finalSelectionOrder.length > 0 ? finalSelectionOrder : null;
        
        return {
            attribute_value_ids,
            attribute_custom_values,
            price_extra,
        };
    },
});

/**
 * Patch PosStore to capture selection order when creating orderline
 */
patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        // Call original
        const result = await super.addLineToOrder(vals, order, opts, configure);
        
        // If we have pending selection order, apply it to the newly created line
        if (_pendingSelectionOrder && result) {
            result._attributeSelectionOrder = [..._pendingSelectionOrder];
            // Rebuild the full product name with correct order
            if (typeof result.set_full_product_name === 'function') {
                result.set_full_product_name();
            }
            _pendingSelectionOrder = null;
        }
        
        return result;
    },
});

/**
 * Patch PosOrderline to use selection order when building product name
 */
patch(PosOrderline.prototype, {
    /**
     * Override set_full_product_name to respect selection order
     */
    set_full_product_name() {
        let attributeString = "";

        if (this.attribute_value_ids && this.attribute_value_ids.length > 0) {
            // Get attribute values
            let attrValues = [...this.attribute_value_ids];
            
            // Sort by selection order if available
            if (this._attributeSelectionOrder && this._attributeSelectionOrder.length > 0) {
                const order = this._attributeSelectionOrder;
                attrValues.sort((a, b) => {
                    const orderA = order.indexOf(a.id);
                    const orderB = order.indexOf(b.id);
                    if (orderA === -1 && orderB === -1) return 0;
                    if (orderA === -1) return 1;
                    if (orderB === -1) return -1;
                    return orderA - orderB;
                });
            }
            
            // Build attribute string
            for (const value of attrValues) {
                if (value.is_custom) {
                    const customValue = this.custom_attribute_value_ids?.find(
                        (cus) =>
                            cus.custom_product_template_attribute_value_id?.id == parseInt(value.id)
                    );
                    if (customValue) {
                        attributeString += `${value.attribute_id.name}: ${value.name}: ${customValue.custom_value}, `;
                    }
                } else {
                    attributeString += `${value.name}, `;
                }
            }

            attributeString = attributeString.slice(0, -2);
            attributeString = ` (${attributeString})`;
        }

        this.full_product_name = `${this.product_id?.display_name || ''}${attributeString}`;
    },
});

console.log("✅ Attribute selection order patch loaded (multi-attribute support)");
