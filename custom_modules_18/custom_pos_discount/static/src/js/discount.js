import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { useRef } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.showDiscountInput = false;
        this.showPriceInput = false;
        this.discountInputRef = useRef("percentInput");
        this.priceInputRef = useRef("priceInput");
    },

    togglePercentInput(state) {
        this.showDiscountInput = state;
        this.render();
        if (state) {
            setTimeout(() => {
                if (this.discountInputRef.el) {
                    this.discountInputRef.el.focus();
                }
            }, 50);
        }
    },

    onPercentKey(ev) {
        if (ev.key === "Enter") {
            const value = parseFloat(ev.target.value);
            if (!isNaN(value) && value >= 0) {
                const order = this.pos.get_order();
                const line = order?.get_selected_orderline();
                if (order && line) {
                    const lineTotal = line.get_price_with_tax();
                    if (lineTotal > 0) {
                        const amountDiscount = value;
                        const percent = Math.min(100, (amountDiscount / lineTotal) * 100);
                        line.set_discount(percent);

                        // Refresh totals
                        order.recomputeOrderData();
                    }
                }
            }
            this.togglePercentInput(false);
        }
    },

    togglePriceInput(state) {
        this.showPriceInput = state;
        this.render();
        if (state) {
            setTimeout(() => {
                if (this.priceInputRef.el) {
                    this.priceInputRef.el.focus();
                }
            }, 50);
        }
    },

    onPriceKey(ev) {
        if (ev.key === "Enter") {
            const newPrice = parseFloat(ev.target.value);
            if (!isNaN(newPrice) && newPrice >= 0) {
                const order = this.pos.get_order();
                const line = order?.get_selected_orderline();
                if (order && line) {
                    const originalPrice = line.get_price_with_tax();
                    if (originalPrice > 0) {
                        // Calculate discount percentage: ((original - new) / original) * 100
                        const discountPercent = Math.max(0, Math.min(100, ((originalPrice - newPrice) / originalPrice) * 100));
                        line.set_discount(discountPercent);

                        // Refresh totals
                        order.recomputeOrderData();
                    }
                }
            }
            this.togglePriceInput(false);
        }
    },

});

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                barcode: { type: String, optional: true },
            },
        },
    },
});

// No extra patch on PosOrderline needed; we rely on built-in `discount`

// Receipt discount total extension removed; standard POS handles discount lines

// Patch PosOrder to include customer data in receipt export
patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(baseUrl, headerData);
        const partner = this.get_partner();
        
        if (partner) {
            result.customer = {
                name: partner.name,
                address: this._getCustomerAddress(partner),
                phone: partner.phone || "",
                mobile: partner.mobile || "",
            };
        }
        
        return result;
    },
    
    _getCustomerAddress(partner) {
        const addressParts = [];
        
        if (partner.street) addressParts.push(partner.street);
        if (partner.street2) addressParts.push(partner.street2);
        if (partner.city) addressParts.push(partner.city);
        if (partner.state_id && partner.state_id.name) addressParts.push(partner.state_id.name);
        if (partner.zip) addressParts.push(partner.zip);
        if (partner.country_id && partner.country_id.name) addressParts.push(partner.country_id.name);
        
        return addressParts.join(', ');
    },
});
