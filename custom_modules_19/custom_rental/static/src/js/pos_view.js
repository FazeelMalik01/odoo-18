

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";

const COLLECTION_ID = "68360a7c8d2bb90e61d3883f";

class RentalPosPage extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            page: "products",
            products: [],
            loading: true,
            expandedCard: null,
            expandedDate: "",
            expandedStartTime: "",
            expandedEndTime: "",
            cart: [],
            pricingSelections: {},
            addonProducts: [],
            addonsLoading: false,
            // checkout
            showCustomerDialog: false,
            customerSearch: "",
            customerResults: [],
            customerSearchLoading: false,
            activeAccordion: "customer",
            billing: {
                selectedPartnerId: false,
                firstName: "",
                lastName: "",
                company: "",
                email: "",
                phone: "",
                secondaryPhone: "",
                address: "",
                zip: "",
                city: "",
                state: "",
                referral: "",
            },
            event: {
                locationName: "",
                sameAsBilling: false,
                address: "",
                city: "",
                state: "",
                zip: "",
                zipStatus: null,
                zipRecord: null,
                eventType: "",
                damageWaiver: "yes",
                eventLocation: "",
            },
            additional: {
                weatherPolicyAgreed: false,
                setupTermsAgreed: false,
                setupSurface: "",
                generalDiscount: 0,
                discountApplied: false,
                couponCode: "",
                couponApplied: false,
                couponDiscount: 0,
                couponError: "",
                couponLabel: "",
                internalNotes: "",
                overrideTravelFee: 0,
                depositPercent: 0,
                overrideTaxAmount: 0,
                miscellaneousFees: 0,
            },
            placingOrder: false,
            createdOrderId: null,
            invoiceLoading: false,
            invoiceSent: false,
            invoiceId: null,
            invoiceError: "",
            lastDepositPercent: 0,
            lastCustomerEmail: "",
            lastCustomerPartnerId: false,
        });

        onWillStart(async () => {
            await this.restoreState();
            await this.loadProducts();
        });
    }

    // ── PERSISTENCE ──────────────────────────────────────────
    openRentalOrders() {
        this.action.doAction("sale_renting.rental_order_action");
    }

    async restoreState() {
        try {
            const saved = localStorage.getItem("rental_pos_state");
            if (saved) {
                const data = JSON.parse(saved);
                if (data.cart) this.state.cart = data.cart;
                if (data.pricingSelections) this.state.pricingSelections = data.pricingSelections;
                if (data.page) this.state.page = data.page;
            }
        } catch (e) {
            // no saved state
        }
    }

    async saveState() {
        try {
            const data = JSON.stringify({
                cart: this.state.cart,
                pricingSelections: this.state.pricingSelections,
                page: ["pricing", "checkout"].includes(this.state.page) ? this.state.page : null,
            });
            localStorage.setItem("rental_pos_state", data);
        } catch (e) {
            console.error("Failed to save state", e);
        }
    }

    // ── DATA ─────────────────────────────────────────────────

    async loadProducts() {
        try {
            const products = await this.orm.searchRead(
                "product.template",
                [
                    ["webflow_item_id", "!=", false],
                    ["webflow_collection_id", "=", COLLECTION_ID],
                ],
                ["id", "name", "list_price", "pick_up_price", "drop_off_price",
                    "default_code", "description_sale", "pdf_url", "website_url",
                    "webflow_category", "image_128"],
                { limit: 100 }
            );
            this.state.products = products;
        } catch (e) {
            console.error("Failed to load products", e);
        } finally {
            this.state.loading = false;
        }
    }

    // ── INLINE CARD EXPAND ───────────────────────────────────

    toggleExpand(product) {
        if (this.state.expandedCard === product.id) {
            this.state.expandedCard = null;
            this.state.expandedDate = "";
            this.state.expandedStartTime = "";
            this.state.expandedEndTime = "";
        } else {
            this.state.expandedCard = product.id;
            this.state.expandedDate = "";
            this.state.expandedStartTime = "";
            this.state.expandedEndTime = "";
        }
    }

    addToCart(product, isMainProduct = false) {
        if (!this.state.expandedDate || !this.state.expandedStartTime || !this.state.expandedEndTime) {
            alert("Please fill in date, start time, and end time.");
            return;
        }

        const cartItemId = Date.now();
        this.state.cart = [...this.state.cart, {
            id: cartItemId,
            productId: product.id,
            parentProductId: isMainProduct ? product.id : product.id,
            name: product.name,
            image_128: product.image_128,
            default_code: product.default_code,
            list_price: product.list_price,
            pick_up_price: product.pick_up_price,
            drop_off_price: product.drop_off_price,
            date: this.state.expandedDate,
            startTime: this.state.expandedStartTime,
            endTime: this.state.expandedEndTime,
            isAddon: false,
        }];

        this.state.pricingSelections = {
            ...this.state.pricingSelections,
            [cartItemId]: "staffed",
        };

        this.state.expandedCard = null;
        this.state.expandedDate = "";
        this.state.expandedStartTime = "";
        this.state.expandedEndTime = "";

        this.saveState();
    }

    addAddonToCart(addon) {
        const cartItemId = Date.now();
        this.state.cart = [...this.state.cart, {
            id: cartItemId,
            productId: addon.id,
            parentProductId: addon.id,
            name: addon.name,
            image_128: addon.image_128,
            default_code: addon.default_code,
            list_price: addon.list_price,
            pick_up_price: addon.pick_up_price,
            drop_off_price: addon.drop_off_price,
            date: "",
            startTime: "",
            endTime: "",
            isAddon: true,
        }];
        this.state.pricingSelections = {
            ...this.state.pricingSelections,
            [cartItemId]: "staffed",
        };
        this.saveState();
    }

    removeFromCart(itemId) {
        this.state.cart = this.state.cart.filter(i => i.id !== itemId);
        const updated = { ...this.state.pricingSelections };
        delete updated[itemId];
        this.state.pricingSelections = updated;
        this.saveState();
    }

    // ── NAVIGATION ───────────────────────────────────────────

    goBack() {
        if (this.state.page === "checkout") {
            this.state.page = "pricing";
        } else if (this.state.page === "pricing") {
            this.state.page = "products";
            this.state.expandedCard = null;
            this.state.addonProducts = [];
        } else {
            this.state.page = "products";
            this.state.expandedCard = null;
        }
        this.saveState();
    }

    async goToPricing() {
        if (this.state.cart.length === 0) {
            alert("Your cart is empty.");
            return;
        }
        this.state.page = "pricing";
        this.state.addonsLoading = true;
        this.state.addonProducts = [];
        this.saveState();

        try {
            const productIds = [...new Set(
                this.state.cart
                    .filter(i => !i.isAddon)
                    .map(i => i.parentProductId || i.productId)
            )];

            const lineItems = await this.orm.searchRead(
                "webflow.line.item",
                [["product_tmpl_id", "in", productIds]],
                ["id", "line_item_id"],
            );

            const lineItemIds = lineItems.map(l => l.line_item_id).filter(Boolean);

            if (lineItemIds.length) {
                const addons = await this.orm.searchRead(
                    "product.template",
                    [["webflow_item_id", "in", lineItemIds]],
                    ["id", "name", "list_price", "pick_up_price", "drop_off_price",
                        "default_code", "image_128", "webflow_item_id"],
                );
                this.state.addonProducts = addons;
            }
        } catch (e) {
            console.error("Failed to load addons", e);
        } finally {
            this.state.addonsLoading = false;
        }
    }

    goToCheckout() {
        this.state.page = "checkout";
        this.saveState();
    }

    continueShopping() {
        this.state.page = "products";
        this.state.expandedCard = null;
        this.state.addonProducts = [];
        this.saveState();
    }

    // ── PRICING ──────────────────────────────────────────────

    setPriceType(itemId, type) {
        this.state.pricingSelections = {
            ...this.state.pricingSelections,
            [itemId]: type,
        };
        this.saveState();
    }

    getDurationHours(date, startTime, endTime) {
        if (!date || !startTime || !endTime) return 1;
        try {
            const [sh, sm] = startTime.split(":").map(Number);
            const [eh, em] = endTime.split(":").map(Number);

            let startMinutes = sh * 60 + sm;
            let endMinutes = eh * 60 + em;

            // Overnight — end is next day
            if (endMinutes <= startMinutes) {
                endMinutes += 24 * 60;
            }

            const durationHours = (endMinutes - startMinutes) / 60;
            return Math.max(1, durationHours); // minimum 1 hour
        } catch (e) {
            return 1;
        }
    }

    /**
     * Get price for a cart item: unit_price × timeslots
     */
    getExtraTimeCharge(date, startTime, endTime) {
        if (!date || !startTime || !endTime) return 0;
        const hours = this.getDurationHours(date, startTime, endTime);
        const totalMinutes = hours * 60;
        const slots = Math.ceil(totalMinutes / 15);
        return slots * 25;
    }

    getItemPrice(item) {
        const type = this.state.pricingSelections[item.id] || "staffed";
        let unitPrice = 0;
        if (type === "staffed") unitPrice = item.list_price || 0;
        if (type === "pickup") unitPrice = item.pick_up_price || 0;
        if (type === "dropoff") unitPrice = item.drop_off_price || 0;

        if (item.isAddon || !item.date || !item.startTime || !item.endTime) {
            return unitPrice;
        }

        return unitPrice + this.getExtraTimeCharge(item.date, item.startTime, item.endTime);
    }

    /**
     * Get display label for duration e.g. "3.5 hrs"
     */
    getItemDurationLabel(item) {
        if (item.isAddon || !item.date || !item.startTime || !item.endTime) return "";
        const hours = this.getDurationHours(item.date, item.startTime, item.endTime);
        const extra = this.getExtraTimeCharge(item.date, item.startTime, item.endTime);
        const label = hours % 1 === 0 ? `${hours} hrs` : `${hours.toFixed(2)} hrs`;
        return `${label} (+$${extra} time charge)`;
    }

    getCartTotal() {
        return this.state.cart.reduce((sum, item) => sum + this.getItemPrice(item), 0);
    }

    getDiscountAmount() {
        if (!this.state.additional.discountApplied) return 0;
        return this.getCartTotal() * (this.state.additional.generalDiscount / 100);
    }

    getEffectiveTax() {
        const override = this.state.additional.overrideTaxAmount;
        if (override > 0) return override;
        const subtotal = this.getCartTotal();
        const discount = this.getDiscountAmount();
        const coupon = this.state.additional.couponDiscount || 0;
        return Math.max(0, subtotal - discount - coupon) * 0.07;
    }

    getDepositAmount() {
        const percent = this.state.additional.depositPercent || 0;
        if (percent <= 0) return 0;
        const subtotal = this.getCartTotal();
        const discount = this.getDiscountAmount();
        const coupon = this.state.additional.couponDiscount || 0;
        const misc = this.state.additional.miscellaneousFees || 0;
        const tax = this.getEffectiveTax();
        const beforeDeposit = subtotal - discount - coupon + misc + tax;
        return beforeDeposit * (percent / 100);
    }

    getCheckoutGrandTotal() {
        const subtotal = this.getCartTotal();
        const discount = this.getDiscountAmount();
        const coupon = this.state.additional.couponDiscount || 0;
        const misc = this.state.additional.miscellaneousFees || 0;
        const tax = this.getEffectiveTax();
        // deposit is NOT deducted — it's just the first payment portion
        return Math.max(0, subtotal - discount - coupon + misc + tax);
    }

    getGrandTotal() {
        return this.getCartTotal() * 1.07;
    }

    // ── CUSTOMER ─────────────────────────────────────────────

    async searchCustomers(query) {
        if (!query || query.length < 2) {
            this.state.customerResults = [];
            return;
        }
        this.state.customerSearchLoading = true;
        try {
            const results = await this.orm.searchRead(
                "res.partner",
                ["|", ["name", "ilike", query], ["email", "ilike", query]],
                ["id", "name", "email", "phone", "phone_secondary",
                    "company_name", "street", "zip", "city", "state_id"],
                { limit: 10 }
            );
            this.state.customerResults = results;
        } catch (e) {
            console.error("Customer search failed", e);
        } finally {
            this.state.customerSearchLoading = false;
        }
    }

    selectCustomer(partner) {
        const nameParts = (partner.name || "").split(" ");
        this.state.billing = {
            ...this.state.billing,
            selectedPartnerId: partner.id,
            firstName: nameParts[0] || "",
            lastName: nameParts.slice(1).join(" ") || "",
            company: partner.company_name || "",
            email: partner.email || "",
            phone: partner.phone || "",
            secondaryPhone: partner.phone_secondary || "",
            address: partner.street || "",
            zip: partner.zip || "",
            city: partner.city || "",
            state: partner.state_id ? partner.state_id[1] : "",
        };
        this.state.showCustomerDialog = false;
        this.state.customerSearch = "";
        this.state.customerResults = [];
    }

    setBillingField(field, value) {
        this.state.billing = { ...this.state.billing, [field]: value };
    }

    // ── ACCORDION ────────────────────────────────────────────

    setAccordion(name) {
        this.state.activeAccordion = this.state.activeAccordion === name ? null : name;
    }

    // ── EVENT ────────────────────────────────────────────────

    setEventField(field, value) {
        this.state.event = { ...this.state.event, [field]: value };
    }

    async toggleSameAsBilling(checked) {
        this.state.event.sameAsBilling = checked;
        if (checked) {
            this.state.event.address = this.state.billing.address;
            this.state.event.city = this.state.billing.city;
            this.state.event.state = this.state.billing.state;
            this.state.event.zip = this.state.billing.zip;
            await this.verifyEventZip(this.state.billing.zip);
        } else {
            this.state.event.zipStatus = null;
            this.state.event.zipRecord = null;
        }
    }

    async verifyEventZip(zip) {
        if (!zip || zip.length < 3) {
            this.state.event.zipStatus = null;
            return;
        }
        try {
            const result = await this.orm.searchRead(
                "rental.zipcode",
                [["name", "=", zip]],
                ["id", "name", "city", "state_id"],
                { limit: 1 }
            );
            if (result.length > 0) {
                this.state.event.zipStatus = "available";
                this.state.event.zipRecord = result[0];
            } else {
                this.state.event.zipStatus = "not_available";
                this.state.event.zipRecord = null;
            }
        } catch (e) {
            console.error("Zip verification failed", e);
        }
    }

    // ── ADDITIONAL ───────────────────────────────────────────

    setAdditionalField(field, value) {
        this.state.additional = { ...this.state.additional, [field]: value };
    }

    applyDiscount() {
        const discount = this.state.additional.generalDiscount;
        if (!discount || discount <= 0) return;
        this.state.additional.discountApplied = true;
    }

    onDiscountChange(e) {
        const val = parseFloat(e.target.value) || 0;
        this.setAdditionalField('generalDiscount', val);
        this.setAdditionalField('discountApplied', false);
    }

    onDepositPercentChange(e) {
        this.setAdditionalField('depositPercent', parseFloat(e.target.value) || 0);
    }

    onOverrideTaxChange(e) {
        this.setAdditionalField('overrideTaxAmount', parseFloat(e.target.value) || 0);
    }

    onMiscFeesChange(e) {
        this.setAdditionalField('miscellaneousFees', parseFloat(e.target.value) || 0);
    }

    onOverrideTravelFeeChange(e) {
        this.setAdditionalField('overrideTravelFee', parseFloat(e.target.value) || 0);
    }

    async applyCoupon() {
        const code = this.state.additional.couponCode;
        if (!code) {
            alert("Please enter a coupon code.");
            return;
        }
        try {
            const cards = await this.orm.searchRead(
                "loyalty.card",
                [["code", "=", code], ["active", "=", true]],
                ["id", "code", "points", "expiration_date", "program_id", "partner_id"],
                { limit: 1 }
            );

            if (!cards.length) {
                this.state.additional.couponApplied = false;
                this.state.additional.couponDiscount = 0;
                this.state.additional.couponError = "Coupon code not found.";
                return;
            }

            const card = cards[0];

            if (card.expiration_date) {
                const expiry = new Date(card.expiration_date);
                if (expiry < new Date()) {
                    this.state.additional.couponApplied = false;
                    this.state.additional.couponDiscount = 0;
                    this.state.additional.couponError = "This coupon has expired.";
                    return;
                }
            }

            const programId = card.program_id[0];
            const rewards = await this.orm.searchRead(
                "loyalty.reward",
                [["program_id", "=", programId], ["reward_type", "=", "discount"]],
                ["id", "discount", "discount_mode", "discount_max_amount", "reward_type"],
                { limit: 1 }
            );

            if (!rewards.length) {
                this.state.additional.couponApplied = false;
                this.state.additional.couponDiscount = 0;
                this.state.additional.couponError = "No discount reward found for this coupon.";
                return;
            }

            const reward = rewards[0];
            const subtotal = this.getCartTotal();
            let discountAmount = 0;

            if (reward.discount_mode === "percent") {
                discountAmount = subtotal * (reward.discount / 100);
                if (reward.discount_max_amount > 0) {
                    discountAmount = Math.min(discountAmount, reward.discount_max_amount);
                }
            } else if (reward.discount_mode === "per_point") {
                discountAmount = card.points * reward.discount;
            } else {
                discountAmount = reward.discount;
            }

            this.state.additional.couponApplied = true;
            this.state.additional.couponDiscount = discountAmount;
            this.state.additional.couponError = "";
            this.state.additional.couponLabel = `${card.program_id[1]} (${reward.discount_mode === "percent" ? reward.discount + "%" : "$" + reward.discount})`;

        } catch (e) {
            console.error("Coupon lookup failed", e);
            this.state.additional.couponError = "Failed to verify coupon.";
        }
    }

    // ── PLACE ORDER ──────────────────────────────────────────
    async placeOrder() {
        if (!this.state.additional.weatherPolicyAgreed || !this.state.additional.setupTermsAgreed) {
            alert("Please agree to both policies before placing the order.");
            return;
        }

        try {
            this.state.placingOrder = true;

            // ── 1. Partner ─────────────────────────────────────
            const fullName = `${this.state.billing.firstName} ${this.state.billing.lastName}`.trim();
            let partnerId = false;

            if (this.state.billing.selectedPartnerId) {
                partnerId = this.state.billing.selectedPartnerId;
            } else if (fullName) {
                const createdPartner = await this.orm.create("res.partner", [{
                    name: fullName,
                    email: this.state.billing.email || false,
                    phone: this.state.billing.phone || false,
                    phone_secondary: this.state.billing.secondaryPhone || false,
                    street: this.state.billing.address || false,
                    zip: this.state.billing.zip || false,
                    city: this.state.billing.city || false,
                    company_name: this.state.billing.company || false,
                }]);
                partnerId = Array.isArray(createdPartner) ? createdPartner[0] : createdPartner;
            }

            // ── 2. UTC converter ───────────────────────────────
            // Odoo stores datetimes in UTC.
            // new Date("YYYY-MM-DDTHH:MM:00") parses as LOCAL time,
            // then .getUTCxxx() gives the UTC equivalent to pass to Odoo.
            const toOdooUTC = (dateStr, timeStr) => {
                if (!dateStr || !timeStr) return false;
                const localDate = new Date(`${dateStr}T${timeStr}:00`);
                const pad = n => String(n).padStart(2, "0");
                return (
                    `${localDate.getUTCFullYear()}-` +
                    `${pad(localDate.getUTCMonth() + 1)}-` +
                    `${pad(localDate.getUTCDate())} ` +
                    `${pad(localDate.getUTCHours())}:` +
                    `${pad(localDate.getUTCMinutes())}:00`
                );
            };

            // ── 3. Fetch 7% sales tax once (outside loop) ─────
            const taxRecords = await this.orm.searchRead(
                "account.tax",
                [
                    ["name", "ilike", "7%"],
                    ["type_tax_use", "=", "sale"],
                    ["active", "=", true],
                ],
                ["id", "name"],
                { limit: 1 }
            );
            const saleTaxId = taxRecords.length ? taxRecords[0].id : false;

            // ── 4. Order lines ─────────────────────────────────
            const orderLines = [];

            for (const item of this.state.cart) {
                const variants = await this.orm.searchRead(
                    "product.product",
                    [["product_tmpl_id", "=", item.productId]],
                    ["id"],
                    { limit: 1 }
                );

                if (!variants.length) continue;

                const productVariantId = variants[0].id;

                // getItemPrice() = unitPrice + (ceil(totalMinutes/15) x $25)
                // Exactly what the POS UI shows — pass as price_unit with qty=1
                const lineTotal = this.getItemPrice(item);

                // Build start/end in UTC for Odoo
                let startDate = false;
                let endDate = false;

                if (item.date && item.startTime) {
                    startDate = toOdooUTC(item.date, item.startTime);
                }
                if (item.date && item.endTime) {
                    // Detect overnight: if end <= start it rolls to next day
                    const [sh, sm] = (item.startTime || "00:00").split(":").map(Number);
                    const [eh, em] = item.endTime.split(":").map(Number);
                    const endDay = (eh < sh || (eh === sh && em < sm))
                        ? this._addDays(item.date, 1)
                        : item.date;
                    endDate = toOdooUTC(endDay, item.endTime);
                }

                orderLines.push([0, 0, {
                    product_id: productVariantId,
                    product_uom_qty: 1,
                    price_unit: lineTotal,
                    is_rental: true,
                    // Explicitly set the 7% sales tax on each line
                    ...(saleTaxId && { tax_ids: [[6, 0, [saleTaxId]]] }),
                    ...(startDate && { start_date: startDate }),
                    ...(endDate && { return_date: endDate }),
                }]);
            }

            // ── 5. Rental start date on order header ──────────
            const firstItem = this.state.cart.find(i => i.date && i.startTime);
            const orderRentalStart = firstItem
                ? toOdooUTC(firstItem.date, firstItem.startTime)
                : false;

            // ── 6. Create order ────────────────────────────────
            const orderVals = {
                partner_id: partnerId,
                is_rental_order: true,
                ...(orderRentalStart && { rental_start_date: orderRentalStart }),

                event_location_name: this.state.event.locationName || false,
                event_same_as_billing: this.state.event.sameAsBilling,
                event_street: this.state.event.address || false,
                event_city: this.state.event.city || false,
                event_zip: this.state.event.zip || false,
                event_type: this.state.event.eventType || false,
                damage_waiver: this.state.event.damageWaiver || "yes",
                event_location: this.state.event.eventLocation || false,

                additional_weather_policy_agreed: this.state.additional.weatherPolicyAgreed,
                additional_setup_terms_agreed: this.state.additional.setupTermsAgreed,
                setup_surface: this.state.additional.setupSurface || false,
                general_discount: this.state.additional.generalDiscount || 0,
                internal_notes: this.state.additional.internalNotes || false,

                override_travel_fee: this.state.additional.overrideTravelFee || 0,
                // 0 = use Odoo product tax, >0 = override (for email template)
                override_tax_amount: this.state.additional.overrideTaxAmount || 0,
                miscellaneous_fees: this.state.additional.miscellaneousFees || 0,
                override_deposit_amount: this.getDepositAmount(),

                order_line: orderLines,
            };

            const createdOrder = await this.orm.create("sale.order", [orderVals], {
                context: {
                    in_rental_app: 1,
                    default_is_rental_order: 1,
                }
            });

            const orderId = Array.isArray(createdOrder) ? createdOrder[0] : createdOrder;
            this.state.lastDepositPercent = this.state.additional.depositPercent || 0;
            this.state.lastCustomerEmail = this.state.billing.email || "";
            this.state.lastCustomerPartnerId = this.state.billing.selectedPartnerId || false;

            // ── 7. Clear state ─────────────────────────────────
            this.state.cart = [];
            this.state.pricingSelections = {};
            this.state.billing = {
                selectedPartnerId: false, firstName: "", lastName: "",
                company: "", email: "", phone: "", secondaryPhone: "",
                address: "", zip: "", city: "", state: "", referral: "",
            };
            this.state.event = {
                locationName: "", sameAsBilling: false, address: "",
                city: "", state: "", zip: "", zipStatus: null,
                zipRecord: null, eventType: "", damageWaiver: "yes", eventLocation: "",
            };
            this.state.additional = {
                weatherPolicyAgreed: false, setupTermsAgreed: false,
                setupSurface: "", generalDiscount: 0, discountApplied: false,
                couponCode: "", couponApplied: false, couponDiscount: 0,
                couponError: "", couponLabel: "", internalNotes: "",
                overrideTravelFee: 0, depositPercent: 0,
                overrideTaxAmount: 0, miscellaneousFees: 0,
            };
            localStorage.removeItem("rental_pos_state");

            this.state.createdOrderId = orderId;
            this.state.page = "success";

        } catch (e) {
            console.error("Failed to place order", e);
            alert(`Failed to create order: ${e.message || e}`);
        } finally {
            this.state.placingOrder = false;
        }
    }


    _addDays(dateStr, days) {
        const d = new Date(dateStr);
        d.setDate(d.getDate() + days);
        return d.toISOString().split("T")[0];
    }

    openCreatedOrder() {
        window.location.href = `/odoo/rental/${this.state.createdOrderId}`;
    }

    // ── HELPERS ──────────────────────────────────────────────

    getImageSrc(product) {
        if (product && product.image_128) return `data:image/png;base64,${product.image_128}`;
        return "/web/static/img/placeholder.png";
    }

    fmt(val) {
        return (val || 0).toFixed(2);
    }
    async createAndSendInvoice() {
        try {
            this.state.invoiceLoading = true;
            this.state.invoiceError = "";

            const invoiceId = await this.orm.call(
                "sale.order",
                "action_create_and_send_invoice_pos",
                [[this.state.createdOrderId]],
                {
                    deposit_percent: this.state.lastDepositPercent || 0,
                }
            );

            const id = Array.isArray(invoiceId) ? invoiceId[0] : invoiceId;
            this.state.invoiceSent = true;
            this.state.invoiceId = id;

        } catch (e) {
            console.error("Invoice creation failed", e);
            this.state.invoiceError = `Failed: ${e.message || e}`;
        } finally {
            this.state.invoiceLoading = false;
        }
    }

    openInvoice() {
        window.location.href = `/odoo/accounting/customer-invoices/${this.state.invoiceId}`;
    }
    getTimeSlots() {
        const slots = [];
        for (let h = 0; h < 24; h++) {
            for (let m = 0; m < 60; m += 15) {
                const hh = String(h).padStart(2, "0");
                const mm = String(m).padStart(2, "0");
                const value = `${hh}:${mm}`;
                // 12-hour display label
                const period = h < 12 ? "AM" : "PM";
                const displayH = h % 12 === 0 ? 12 : h % 12;
                const label = `${displayH}:${mm} ${period}`;
                slots.push({ value, label });
            }
        }
        return slots;
    }

    getTodayDate() {
        return new Date().toISOString().split("T")[0];
    }
}

RentalPosPage.template = "custom_rental.RentalPosView";
registry.category("actions").add("rental_pos_page", RentalPosPage);

patch(ControlPanel.prototype, {
    setup() {
        super.setup();
        this._actionService = useService("action");
        this.__rentalPosVisible = false;

        onMounted(() => {
            this.__rentalPosVisible = window.location.pathname.includes("/odoo/rental");
            this.render(true);
        });

        onPatched(() => {
            const isRental = window.location.pathname.includes("/odoo/rental");
            if (this.__rentalPosVisible !== isRental) {
                this.__rentalPosVisible = isRental;
                this.render(true);
            }
        });
    },

    get rentalPosVisible() {
        return this.__rentalPosVisible || false;
    },

    openRentalPos() {
        this._actionService.doAction("custom_rental.action_rental_pos_page");
    },
});