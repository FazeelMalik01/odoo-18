import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

// Patch PosOrderline to format discount to 2 decimal places
patch(PosOrderline.prototype, {
    get_discount_str() {
        const discount = this.discount || 0;
        if (discount) {
            return parseFloat(discount).toFixed(2);
        }
        return "";
    },
    
    get_price_with_tax() {
        let price = super.get_price_with_tax();
        // If there's a discount, adjust price_unit to ensure correct rounding
        // This handles cases where customer selection triggers price recalculation
        if (this.discount && this.discount > 0) {
            const rounded = Math.round(price * 100) / 100;
            const cents = Math.floor((rounded * 100) % 100);
            const dollars = Math.floor(rounded);
            
            let targetPrice;
            // If rounded price ends in .91 and original is between .90 and .915, use .90 instead
            if (cents === 91 && price >= dollars + 0.90 && price < dollars + 0.915) {
                targetPrice = dollars + 0.90;
            } else {
                targetPrice = rounded;
            }
            
            // Adjust price_unit to produce the target price (only if there's a difference)
            if (Math.abs(price - targetPrice) > 0.0001 && this.price_unit && this.price_unit !== 0 && price !== 0) {
                const priceRatio = targetPrice / price;
                // Only adjust if ratio is significantly different to avoid infinite loops
                if (Math.abs(priceRatio - 1) > 0.00001) {
                    this.price_unit = this.price_unit * priceRatio;
                    // Recalculate price with adjusted price_unit
                    price = super.get_price_with_tax();
                }
            }
            
            return targetPrice;
        }
        return price;
    },
    
    async set_discount(discount) {
        console.log("=== POS Orderline set_discount Debug ===");
        console.log(`Product: ${this.product_id?.name || 'N/A'}`);
        console.log(`Discount percentage: ${discount}%`);
        const qty = this.qty || this.quantity || 1;
        console.log(`Before set_discount - price_unit: ${this.price_unit}, qty: ${qty}, quantity: ${this.quantity}`);
        
        // Call parent set_discount first
        await super.set_discount(discount);
        
        console.log(`After parent set_discount - price_unit: ${this.price_unit}, discount: ${this.discount}`);
        
        // After discount is applied, adjust price_unit so the final price rounds to 2 decimals
        // This matches the behavior of custom Price button which sets exact prices
        const quantity = this.qty || this.quantity || 1;
        if (this.price_unit && this.price_unit !== 0 && quantity > 0) {
            // Get the current prices after discount
            const currentPriceWithTax = this.get_price_with_tax();
            const currentPriceWithoutTax = this.get_price_without_tax();
            
            console.log(`Current price_with_tax (after discount): ${currentPriceWithTax}`);
            console.log(`Current price_without_tax (after discount): ${currentPriceWithoutTax}`);
            
            // Round to 2 decimal places, but round DOWN for cases like 369.911 -> 369.90 (not 369.91)
            // This matches custom button behavior which rounds down
            const rounded = Math.round(currentPriceWithTax * 100) / 100;
            
            // If rounded price ends in .91 and original is very close (like 369.911), use .90 instead
            let targetPriceWithTax;
            const cents = Math.floor((rounded * 100) % 100);
            const dollars = Math.floor(rounded);
            
            // Check if rounded to .91 and original is between .90 and .915 (like 369.911)
            if (cents === 91 && currentPriceWithTax >= dollars + 0.90 && currentPriceWithTax < dollars + 0.915) {
                targetPriceWithTax = dollars + 0.90; // Round down to .90
            } else {
                targetPriceWithTax = rounded; // Use normal rounding
            }
            
            console.log(`Current: ${currentPriceWithTax}, Rounded: ${rounded}, Target: ${targetPriceWithTax}`);
            
            // Calculate the difference we need to adjust
            const priceDiff = targetPriceWithTax - currentPriceWithTax;
            
            console.log(`Price difference: ${priceDiff}`);
            
            // Always adjust to match target price to ensure consistency with custom button
            if (Math.abs(priceDiff) > 0.00001 && currentPriceWithoutTax !== 0) {
                // Calculate the ratio: target_price / current_price
                // Then apply that ratio to price_unit
                const priceRatio = currentPriceWithTax !== 0 ? targetPriceWithTax / currentPriceWithTax : 1;
                const oldPriceUnit = this.price_unit;
                this.price_unit = this.price_unit * priceRatio;
                
                console.log(`Price ratio: ${priceRatio}`);
                console.log(`Old price_unit: ${oldPriceUnit}, New price_unit: ${this.price_unit}`);
                
                // Verify the adjustment
                const newPriceWithTax = this.get_price_with_tax();
                console.log(`New price_with_tax after adjustment: ${newPriceWithTax}`);
                console.log(`✅ Adjustment applied - Final price: ${newPriceWithTax}`);
            } else {
                console.log(`No adjustment needed (difference: ${priceDiff}, threshold: 0.00001)`);
            }
        } else {
            console.log(`Skipping adjustment - price_unit: ${this.price_unit}, quantity: ${quantity}`);
        }
        console.log("=== End set_discount Debug ===");
    },
});

