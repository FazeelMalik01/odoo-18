/**
 * Add invoice tax labels ("Label on Invoices") to orderline display data
 * so it can be shown on the POS receipt just under the product name.
 */
import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { getTaxesAfterFiscalPosition } from "@point_of_sale/app/models/utils/tax_utils";

// Patch PosOrderline model to add invoiceTaxLabels to display data
patch(PosOrderline.prototype, {
    getDisplayData() {
        const res = super.getDisplayData();
        try {
            // Get tax objects from orderline or product
            let taxObjects = [];
            
            if (this.tax_ids && this.tax_ids.length > 0) {
                taxObjects = this.tax_ids;
            } else {
                taxObjects = getTaxesAfterFiscalPosition(
                    this.product_id.taxes_id,
                    this.order_id.fiscal_position_id,
                    this.models
                ) || [];
            }
            
            // Get full tax objects from models using tax IDs
            const taxModels = this.models["account.tax"];
            const labels = [];
            
            // Extract tax IDs from tax objects
            const taxIds = taxObjects.map(t => {
                if (typeof t === 'number') return t;
                if (t && t.id) return t.id;
                if (t && typeof t === 'object' && 'id' in t) return t.id;
                return null;
            }).filter(id => id !== null);
            
            // Get tax data from models
            for (const taxId of taxIds) {
                let tax = null;
                
                // Try to get tax from models
                if (taxModels && typeof taxModels.get === 'function') {
                    tax = taxModels.get(taxId);
                } else if (taxModels && taxModels.getAllBy) {
                    const allTaxes = taxModels.getAllBy('id');
                    tax = allTaxes[taxId];
                }
                
                if (tax) {
                    // Check if tax type is sale and has invoice_label
                    const taxUse = tax.type_tax_use || "sale";
                    if (taxUse === "sale" && tax.invoice_label) {
                        labels.push(tax.invoice_label);
                    }
                }
            }
            
            res.invoiceTaxLabels = [...new Set(labels)].join(" ");
        } catch (e) {
            console.error("Error getting invoice tax labels:", e);
            res.invoiceTaxLabels = "";
        }
        
        // Add barcode from product to display data
        try {
            if (this.product_id && this.product_id.barcode) {
                res.barcode = this.product_id.barcode;
            } else {
                res.barcode = "";
            }
        } catch (e) {
            console.error("Error getting barcode:", e);
            res.barcode = "";
        }
        
        return res;
    },
});

// Extend Orderline component props to include invoiceTaxLabels
Orderline.props.line.shape.invoiceTaxLabels = { type: String, optional: true };


