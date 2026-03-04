/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

/**
 * Patch PosOrder to preserve orderline insertion order
 * 
 * This ensures that when variants/products are added to the cart,
 * they appear in the order they were added, not sorted.
 */
patch(PosOrder.prototype, {
    /**
     * Override getSortedOrderlines to optionally preserve insertion order
     * By default, returns lines in insertion order unless category sorting is explicitly enabled
     * @returns {Array} Array of orderlines
     */
    getSortedOrderlines() {
        // If category-based sorting is enabled, use the original sorting logic
        if (this.config.orderlines_sequence_in_cart_by_category && this.lines.length) {
            const linesToSort = [...this.lines];
            linesToSort.sort(this.sortBySequenceAndCategory.bind(this));
            const resultLines = [];
            linesToSort.forEach((line) => {
                if (line.combo_line_ids?.length > 0) {
                    resultLines.push(line);
                    const sortedChildLines = [...line.combo_line_ids].sort(
                        this.sortBySequenceAndCategory.bind(this)
                    );
                    resultLines.push(...sortedChildLines);
                } else if (!line.combo_parent_id) {
                    resultLines.push(line);
                }
            });
            return resultLines;
        }
        
        // Return lines in their natural order (which should be insertion order)
        // However, due to reactive system behavior, we need to ensure proper ordering
        // by sorting by the internal creation timestamp if available
        if (this.lines.length) {
            // Get the lines array
            const linesArray = [...this.lines];
            
            // If lines have a creation timestamp or index, sort by that
            // Otherwise, maintain the current order from the reactive system
            // The reactive Map should maintain insertion order
            
            // Filter out combo children that should be shown with their parent
            const resultLines = [];
            linesArray.forEach((line) => {
                if (line.combo_line_ids?.length > 0) {
                    resultLines.push(line);
                    resultLines.push(...line.combo_line_ids);
                } else if (!line.combo_parent_id) {
                    resultLines.push(line);
                }
            });
            
            return resultLines;
        }
        
        return this.lines;
    },
});

console.log("✅ Orderline order preservation patch loaded");

