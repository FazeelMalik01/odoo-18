import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { user } from "@web/core/user";
import { rpc } from "@web/core/network/rpc";

const COLLECTION_ID = "68360a7c8d2bb90e61d3883f";
const MAPBOX_TOKEN = "pk.eyJ1IjoiZmZzc3VwcG9ydCIsImEiOiJjbW1uMWN1cDkxOWxxMnFzYjBldW5ybnU3In0.Df0CoWju8EcZ4PQVH6ag1w";
const TRAVEL_FREE_MILES = 5;       // first 5 miles are free
const TRAVEL_FEE_STAFFED = 2.5;     // $2.50 / mile after free threshold (staffed)
const TRAVEL_FEE_DROPOFF = 3.0;     // $3.00 / mile after free threshold (drop-off)


function newSessionToken() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
        const r = (Math.random() * 16) | 0;
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
}

async function mapboxSuggest(query, sessionToken) {
    if (!query || query.length < 3) return [];
    try {
        const params = new URLSearchParams({
            q: query,
            access_token: MAPBOX_TOKEN,
            session_token: sessionToken,
            country: "us",
            limit: "5",
            types: "address,street,place",
        });
        const res = await fetch(`https://api.mapbox.com/search/searchbox/v1/suggest?${params}`);
        if (!res.ok) return [];
        const data = await res.json();
        return data.suggestions || [];
    } catch (e) {
        console.error("Mapbox suggest error", e);
        return [];
    }
}

async function mapboxRetrieve(mapboxId, sessionToken) {
    try {
        const params = new URLSearchParams({
            access_token: MAPBOX_TOKEN,
            session_token: sessionToken,
        });
        const res = await fetch(
            `https://api.mapbox.com/search/searchbox/v1/retrieve/${encodeURIComponent(mapboxId)}?${params}`
        );
        if (!res.ok) return null;
        const data = await res.json();
        return data.features?.[0]?.properties || null;
    } catch (e) {
        console.error("Mapbox retrieve error", e);
        return null;
    }
}

async function mapboxGeocode(address) {
    if (!address) return null;
    try {
        const params = new URLSearchParams({
            q: address,
            access_token: MAPBOX_TOKEN,
            country: "us",
            limit: "1",
            types: "address,place",
        });
        const res = await fetch(`https://api.mapbox.com/search/searchbox/v1/forward?${params}`);
        if (!res.ok) return null;
        const data = await res.json();
        const feature = data.features?.[0];
        if (!feature) return null;
        const coords = feature.properties?.coordinates || {};
        const geo = feature.geometry?.coordinates;   // [lng, lat]
        return {
            longitude: geo?.[0] ?? coords.longitude ?? null,
            latitude: geo?.[1] ?? coords.latitude ?? null,
        };
    } catch (e) {
        console.error("Mapbox geocode error", e);
        return null;
    }
}

function parseMapboxFeature(props) {
    const ctx = props.context || {};
    const coords = props.coordinates || {};
    return {
        street: props.address || ctx.street?.name || "",
        city: ctx.place?.name || "",
        state: ctx.region?.name || "",
        state_code: ctx.region?.region_code || "",
        zip: ctx.postcode?.name || "",
        country: ctx.country?.name || "",
        country_code: ctx.country?.country_code || "",
        full_address: props.full_address || "",
        latitude: coords.latitude ?? null,
        longitude: coords.longitude ?? null,
    };
}

function haversineDistanceMiles(lat1, lon1, lat2, lon2) {
    const R = 3958.8;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

async function mapboxDrivingDistanceMiles(fromLng, fromLat, toLng, toLat) {
    try {
        const coords = `${fromLng},${fromLat};${toLng},${toLat}`;
        const url = `https://api.mapbox.com/directions/v5/mapbox/driving/${coords}` +
            `?access_token=${MAPBOX_TOKEN}&overview=false`;
        const res = await fetch(url);
        if (!res.ok) return null;
        const data = await res.json();
        const route = data.routes?.[0];
        if (!route) return null;
        // Mapbox returns metres — convert to miles
        return route.distance / 1609.344;
    } catch (e) {
        console.error("[RentalPOS] Directions API error", e);
        return null;
    }
}

async function findNearestWarehouse(custLat, custLng, warehouses) {
    const valid = warehouses.filter(w => w.latitude != null && w.longitude != null);
    if (!valid.length) return null;

    // Step 1 — rank by straight-line distance
    const ranked = valid
        .map(wh => ({
            wh,
            straight: haversineDistanceMiles(custLat, custLng, wh.latitude, wh.longitude),
        }))
        .sort((a, b) => a.straight - b.straight);

    // Step 2 — get real driving distance for up to 3 closest candidates
    const results = await Promise.all(
        ranked.slice(0, 3).map(async ({ wh, straight }) => {
            const driving = await mapboxDrivingDistanceMiles(
                custLng, custLat, wh.longitude, wh.latitude
            );
            return {
                warehouse: wh,
                distanceMiles: driving ?? straight,
                isDriving: driving !== null,
            };
        })
    );

    // Step 3 — pick closest by driving (or haversine fallback)
    results.sort((a, b) => a.distanceMiles - b.distanceMiles);
    return results[0];
}

// ── Debounce ──────────────────────────────────────────────────────────────────
function debounce(fn, delay) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

/** Parse Odoo UTC datetime string to local YYYY-MM-DD and HH:MM for POS cart fields. */
function odooDatetimeToLocalParts(dtStr) {
    if (!dtStr) return { date: "", time: "" };
    const normalized = typeof dtStr === "string" ? dtStr.replace(" ", "T") : "";
    if (!normalized) return { date: "", time: "" };
    const d = new Date(normalized.endsWith("Z") ? normalized : `${normalized}Z`);
    if (Number.isNaN(d.getTime())) return { date: "", time: "" };
    const pad = n => String(n).padStart(2, "0");
    return {
        date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
        time: `${pad(d.getHours())}:${pad(d.getMinutes())}`,
    };
}

// ─────────────────────────────────────────────────────────────────────────────

class RentalPosPage extends Component {
    static props = { ...standardActionServiceProps };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            page: "categories",
            categories: [],
            sections: [],
            categoriesLoading: false,
            categorySearch: "",
            selectedSectionId: null,
            sectionPanelOpen: true,
            selectedCategoryId: null,
            selectedCategoryName: "",
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
            showCustomerDialog: false,
            customerSearch: "",
            customerResults: [],
            customerSearchLoading: false,
            activeAccordion: "customer",
            billing: {
                selectedPartnerId: false,
                firstName: "", lastName: "", company: "",
                email: "", phone: "", secondaryPhone: "",
                address: "", zip: "", city: "", state: "", referral: "",
                latitude: null, longitude: null,
            },
            event: {
                locationName: "",
                sameAsBilling: false,
                address: "", city: "", state: "", zip: "",
                zipStatus: null, zipRecord: null,
                eventType: "", damageWaiver: "yes", eventLocation: "",
                latitude: null, longitude: null,
                stillDeliver: false,
            },
            additional: {
                weatherPolicyAgreed: false,
                setupTermsAgreed: false,
                setupSurface: "",
                generalDiscount: 0, discountApplied: false, discountType: "percent",
                discountDescription: "", miscDescription: "",
                couponCode: "", couponApplied: false, couponDiscount: 0,
                couponError: "", couponLabel: "",
                internalNotes: "",
                customerNotes: "",
                overrideTravelFee: 0,
                depositPercent: 0,
                overrideTaxAmount: null,
                miscellaneousFees: 0,
            },
            payment: {
                enabled: false,
                method: "cash",
                checkNumber: "",
                splitMode: "full",
                customPercent: 100,
                tipMode: "none",
                customTip: 0,
                processing: false,
            },
            travelFeeInfo: null,

            placingOrder: false,
            createdOrderId: null,
            /** When set, POS was opened from an existing sale.order (e.g. calendar); pay flow updates this order. */
            existingPosOrderId: null,
            invoiceLoading: false,
            invoiceSent: false,
            invoiceId: null,
            invoiceError: "",
            lastDepositPercent: 0,
            lastCustomerEmail: "",
            lastCustomerPartnerId: false,
            paidOnSpot: false,

            currentOrderNumber: null,
            orderSequence: 0,
            eventIsInPast: false,
            companySalesTax: { id: false, amount: 7, name: "Sales Tax" },

            billingSuggestions: [], billingAddressLoading: false,
            billingAddressRaw: "", showBillingSuggestions: false,
            eventSuggestions: [], eventAddressLoading: false,
            eventAddressRaw: "", showEventSuggestions: false,

            // ── Edit Date panel ───────────────────────────────────────────────
            showEditDate: false,
            editDateValue: "",
            editStartTime: "",
            editEndTime: "",

            isFreedomFunAdmin: false,

            /** Set when existingPosOrderId: invoice/payment summary for banner under step indicator */
            existingOrderPaymentBanner: null,
        });

        // Warehouse cache – populated in loadWarehouses()
        this._warehouses = [];

        this._billingSessionToken = newSessionToken();
        this._eventSessionToken = newSessionToken();

        this._debouncedBillingSuggest = debounce(async (query) => {
            this.state.billingAddressLoading = true;
            const suggestions = await mapboxSuggest(query, this._billingSessionToken);
            this.state.billingSuggestions = suggestions;
            this.state.billingAddressLoading = false;
            this.state.showBillingSuggestions = suggestions.length > 0;
        }, 300);

        this._debouncedEventSuggest = debounce(async (query) => {
            this.state.eventAddressLoading = true;
            const suggestions = await mapboxSuggest(query, this._eventSessionToken);
            this.state.eventSuggestions = suggestions;
            this.state.eventAddressLoading = false;
            this.state.showEventSuggestions = suggestions.length > 0;
        }, 300);

        onWillStart(async () => {
            const ctx = this.props.action?.context || {};
            const openOrderId = ctx.rental_pos_sale_order_id;
            if (ctx.rental_pos_partner_id) {
                this._prepareFreshCategoriesSession();
                await this.loadPartnerIntoBilling(ctx.rental_pos_partner_id);
            } else if (ctx.rental_pos_fresh_categories) {
                this._prepareFreshCategoriesSession();
            } else if (openOrderId) {
                localStorage.removeItem("rental_pos_state");
                try {
                    await this.loadExistingSaleOrderIntoPos(
                        openOrderId,
                        ctx.rental_pos_initial_page || "payment"
                    );
                } catch (e) {
                    console.error("[RentalPOS] Failed to load sale order from context", e);
                    await this.restoreState();
                }
            } else {
                await this.restoreState();
            }
            await Promise.all([this.loadCategories(), this.loadWarehouses(), this.loadCompanySalesTax(), this.loadUserGroup()]);
            if (["products", "pricing", "checkout"].includes(this.state.page) && this.state.selectedCategoryId) {
                await this.loadProducts();
            }
            if (this.state.cart.length > 0) {
                await this._loadAddons();
            }
            if (this.state.existingPosOrderId) {
                await this.refreshExistingOrderPaymentBanner();
            }
        });
    }

    // ── WAREHOUSES ────────────────────────────────────────────────────────────

    async loadWarehouses() {
        try {
            const warehouses = await this.orm.searchRead(
                "stock.warehouse", [], ["id", "name", "partner_id"]
            );
            if (!warehouses.length) return;

            const partnerIds = warehouses.map(w => w.partner_id?.[0]).filter(Boolean);
            const partners = partnerIds.length
                ? await this.orm.searchRead(
                    "res.partner", [["id", "in", partnerIds]],
                    ["id", "street", "city", "state_id", "zip",
                        "partner_latitude", "partner_longitude"]
                )
                : [];

            const byId = Object.fromEntries(partners.map(p => [p.id, p]));

            const result = [];
            for (const wh of warehouses) {
                const partner = byId[wh.partner_id?.[0]];
                let lat = partner?.partner_latitude || null;
                let lng = partner?.partner_longitude || null;

                if ((!lat || lat === 0) && partner) {
                    const addr = [partner.street, partner.city, partner.state_id?.[1], partner.zip]
                        .filter(Boolean).join(", ");
                    if (addr) {
                        const geo = await mapboxGeocode(addr);
                        if (geo?.latitude && geo?.longitude) {
                            lat = geo.latitude;
                            lng = geo.longitude;
                            try {
                                await this.orm.write("res.partner", [partner.id], {
                                    partner_latitude: lat, partner_longitude: lng,
                                });
                            } catch (_) { /* non-critical */ }
                        }
                    }
                }
                result.push({ id: wh.id, name: wh.name, latitude: lat, longitude: lng });
            }

            this._warehouses = result;
            console.log("[RentalPOS] Warehouses:", this._warehouses);
        } catch (e) {
            console.error("[RentalPOS] loadWarehouses failed", e);
        }
    }

    _isAllPickup() {
        const nonAddons = this.state.cart.filter(i => !i.isAddon);
        if (!nonAddons.length) return false;
        return nonAddons.every(i => (this.state.pricingSelections[i.id] || "staffed") === "pickup");
    }

    async _applyTravelFee(custLat, custLng) {
        if (custLat == null || custLng == null || !this._warehouses.length) {
            this.state.travelFeeInfo = null;
            return;
        }

        // Pickup-only orders: customer collects, no travel fee
        if (this._isAllPickup()) {
            this.state.additional = { ...this.state.additional, overrideTravelFee: 0 };
            this.state.travelFeeInfo = null;
            return;
        }

        const nearest = await findNearestWarehouse(custLat, custLng, this._warehouses);
        if (!nearest) { this.state.travelFeeInfo = null; return; }

        const miles = nearest.distanceMiles;
        const type = nearest.isDriving ? "driving" : "straight-line";
        const billable = Math.max(0, miles - TRAVEL_FREE_MILES);

        const hasDropoff = Object.values(this.state.pricingSelections).some(t => t === "dropoff");
        const ratePerMile = hasDropoff ? TRAVEL_FEE_DROPOFF : TRAVEL_FEE_STAFFED;
        const fee = Math.round(billable * ratePerMile * 100) / 100;

        this.state.additional = { ...this.state.additional, overrideTravelFee: fee };
        this.state.travelFeeInfo = {
            distanceMiles: Math.round(miles * 10) / 10,
            billableMiles: Math.round(billable * 10) / 10,
            warehouseName: nearest.warehouse.name,
            isDriving: nearest.isDriving,
            ratePerMile,
        };
        console.log(`[RentalPOS] Travel fee (${type}): ${miles.toFixed(1)} mi, ${billable.toFixed(1)} billable @ $${ratePerMile}/mi from "${nearest.warehouse.name}" → $${fee}`);
    }

    // ── COMPANY SALES TAX ─────────────────────────────────────────────────────

    async _getActiveCompanyId() {
        // Always resolve fresh so company switcher changes are reflected immediately.
        try {
            const info = await rpc("/web/session/get_session_info", {});
            const currentCompany = info?.user_companies?.current_company;
            console.log("[RentalPOS][TAX] session info", {
                current_company: currentCompany,
                company_id: info?.company_id,
                allowed_companies: info?.user_companies?.allowed_companies,
            });
            if (typeof currentCompany === "number" && currentCompany > 0) return currentCompany;
            if (typeof currentCompany === "string" && currentCompany.trim()) {
                const parsed = parseInt(currentCompany, 10);
                if (!Number.isNaN(parsed) && parsed > 0) return parsed;
            }
            if (Array.isArray(currentCompany) && currentCompany[0]) return currentCompany[0];
            if (currentCompany?.id) return currentCompany.id;
            return info?.company_id || user?.companyId || false;
        } catch (_) {
            console.warn("[RentalPOS][TAX] failed to fetch session info; falling back to user.companyId");
            return user?.companyId || false;
        }
    }

    async loadCompanySalesTax() {
        try {
            // Ensure multi-company users can read the correct company's tax.
            // Force search in the active company only to avoid record-rule access errors.
            const activeCompanyId = await this._getActiveCompanyId();
            const ctx = activeCompanyId
                ? { allowed_company_ids: [activeCompanyId], force_company: activeCompanyId }
                : {};
            console.log("[RentalPOS][TAX] loading company default tax", {
                activeCompanyId,
                context: ctx,
            });
            // Reset cached value before loading active-company default.
            this.state.companySalesTax = { id: false, amount: 0, name: "Sales Tax" };
            if (activeCompanyId) {
                const [company] = await this.orm.read(
                    "res.company",
                    [activeCompanyId],
                    ["account_sale_tax_id"],
                    { context: ctx }
                );
                console.log("[RentalPOS][TAX] company.account_sale_tax_id", {
                    company_id: activeCompanyId,
                    account_sale_tax_id: company?.account_sale_tax_id,
                });
                const tax = company?.account_sale_tax_id;
                if (tax && tax[0]) {
                    const [taxRow] = await this.orm.read(
                        "account.tax",
                        [tax[0]],
                        ["id", "name", "amount"],
                        { context: ctx }
                    );
                    if (taxRow?.id) {
                        this.state.companySalesTax = { id: taxRow.id, amount: taxRow.amount, name: taxRow.name };
                        console.log("[RentalPOS][TAX] loaded default sales tax", this.state.companySalesTax);
                        return;
                    }
                    console.warn("[RentalPOS][TAX] account_sale_tax_id set but tax row unreadable", {
                        tax_id: tax[0],
                    });
                }
                console.warn("[RentalPOS][TAX] no default sales tax configured on company", {
                    company_id: activeCompanyId,
                });
            }

            // Do NOT fallback to account.tax sequence.
            // If no default tax is configured in company settings, keep tax at 0 until user overrides.
        } catch (e) {
            console.error("[RentalPOS] Failed to load company sales tax", e);
        }
    }

    // ── PERSISTENCE ───────────────────────────────────────────────────────────

    openRentalOrders() { this.action.doAction("sale_renting.rental_order_action"); }

    async restoreState() {
        try {
            const activeCompanyId = await this._getActiveCompanyId();
            const saved = localStorage.getItem("rental_pos_state");
            if (saved) {
                const data = JSON.parse(saved);
                // If the saved state was created under another company, drop it to avoid cross-company IDs (taxes, etc.).
                if (data.companyId && activeCompanyId && data.companyId !== activeCompanyId) {
                    localStorage.removeItem("rental_pos_state");
                    return;
                }
                if (data.cart) this.state.cart = data.cart;
                if (data.pricingSelections) this.state.pricingSelections = data.pricingSelections;
                if (data.selectedCategoryId) this.state.selectedCategoryId = data.selectedCategoryId;
                if (data.selectedCategoryName) this.state.selectedCategoryName = data.selectedCategoryName;
                if (data.page && ["pricing", "checkout", "products", "payment"].includes(data.page)) {
                    this.state.page = data.page;
                }
                if (data.existingPosOrderId) {
                    this.state.existingPosOrderId = data.existingPosOrderId;
                }
            }
        } catch (e) { /* no saved state */ }
    }

    async saveState() {
        try {
            const activeCompanyId = await this._getActiveCompanyId();
            localStorage.setItem("rental_pos_state", JSON.stringify({
                cart: this.state.cart,
                pricingSelections: this.state.pricingSelections,
                selectedCategoryId: this.state.selectedCategoryId,
                selectedCategoryName: this.state.selectedCategoryName,
                page: ["pricing", "checkout", "products", "payment"].includes(this.state.page) ? this.state.page : null,
                existingPosOrderId: this.state.existingPosOrderId || null,
                companyId: activeCompanyId || null,
            }));
        } catch (e) { console.error("Failed to save state", e); }
    }

    /**
     * Hydrate POS state from a DB sale.order (e.g. calendar click) and jump to checkout/payment.
     */
    async loadPartnerIntoBilling(partnerId) {
        try {
            const partners = await this.orm.read("res.partner", [partnerId], [
                "name", "email", "phone", "phone_secondary", "street", "zip", "city",
                "state_id", "company_name", "partner_latitude", "partner_longitude",
            ]);
            const partner = partners[0];
            if (!partner) return;
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
                latitude: partner.partner_latitude ?? null,
                longitude: partner.partner_longitude ?? null,
            };
            this.state.billingAddressRaw = partner.street || "";
        } catch (e) {
            console.error("[RentalPOS] Failed to pre-fill partner billing", e);
        }
    }

    async loadExistingSaleOrderIntoPos(orderId, targetPage = "payment") {
        const orders = await this.orm.read("sale.order", [orderId], [
            "partner_id", "state", "is_rental_order",
            "event_location_name", "event_same_as_billing", "event_street", "event_city", "event_zip", "event_state_id",
            "event_type", "damage_waiver", "event_location", "event_latitude", "event_longitude",
            "additional_weather_policy_agreed", "additional_setup_terms_agreed", "setup_surface",
            "general_discount", "internal_notes", "customer_notes", "override_travel_fee", "override_tax_amount", "miscellaneous_fees",
            "how_did_you_hear", "tip",
        ]);
        if (!orders?.length) throw new Error("Sale order not found");
        const so = orders[0];

        let partner = null;
        if (so.partner_id?.[0]) {
            const partners = await this.orm.read("res.partner", [so.partner_id[0]], [
                "name", "email", "phone", "phone_secondary", "street", "zip", "city", "state_id",
                "company_name", "partner_latitude", "partner_longitude",
            ]);
            partner = partners[0] || null;
        }

        if (partner) {
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
                referral: so.how_did_you_hear || "",
                latitude: partner.partner_latitude ?? null,
                longitude: partner.partner_longitude ?? null,
            };
            this.state.billingAddressRaw = partner.street || "";
        }

        this.state.event = {
            ...this.state.event,
            locationName: so.event_location_name || "",
            sameAsBilling: !!so.event_same_as_billing,
            address: so.event_street || "",
            city: so.event_city || "",
            state: so.event_state_id ? so.event_state_id[1] : "",
            zip: so.event_zip || "",
            zipStatus: null,
            zipRecord: null,
            eventType: so.event_type || "",
            damageWaiver: so.damage_waiver || "yes",
            eventLocation: so.event_location || "",
            latitude: so.event_latitude ?? null,
            longitude: so.event_longitude ?? null,
            stillDeliver: false,
        };
        this.state.eventAddressRaw = so.event_street || "";

        this.state.additional = {
            ...this.state.additional,
            weatherPolicyAgreed: !!so.additional_weather_policy_agreed,
            setupTermsAgreed: !!so.additional_setup_terms_agreed,
            setupSurface: so.setup_surface || "",
            generalDiscount: so.general_discount || 0,
            discountType: "percent",
            discountDescription: "",
            miscDescription: "",
            internalNotes: so.internal_notes || "",
            customerNotes: so.customer_notes || "",
            overrideTravelFee: so.override_travel_fee || 0,
            overrideTaxAmount: (so.override_tax_amount || 0) > 0 ? so.override_tax_amount : null,
            miscellaneousFees: so.miscellaneous_fees || 0,
        };

        const tipAmt = so.tip || 0;
        this.state.payment = {
            ...this.state.payment,
            tipMode: tipAmt > 0 ? "custom" : "none",
            customTip: tipAmt,
        };

        const lines = await this.orm.searchRead("sale.order.line", [["order_id", "=", orderId]], [
            "id", "product_id", "product_uom_qty", "price_unit", "start_date", "return_date",
            "is_rental", "is_tip", "display_type",
        ]);

        const productIds = [...new Set(lines.filter(l => l.product_id?.[0]).map(l => l.product_id[0]))];
        const productVariants = productIds.length
            ? await this.orm.read("product.product", productIds, ["product_tmpl_id"])
            : [];
        const tmplIdByProductId = Object.fromEntries(
            productVariants.map(p => [p.id, p.product_tmpl_id?.[0]])
        );
        const tmplIds = [...new Set(Object.values(tmplIdByProductId).filter(Boolean))];
        const templates = tmplIds.length
            ? await this.orm.read("product.template", tmplIds, [
                "id", "name", "list_price", "pick_up_price", "drop_off_price",
                "default_code", "image_128", "categ_id",
                "per_hour_rate", "minimum_booking_hrs", "base_hrs",
            ])
            : [];
        const tmplById = Object.fromEntries(templates.map(t => [t.id, t]));

        const cart = [];
        const pricingSelections = {};
        let idx = 0;
        let firstCategId = null;

        for (const line of lines) {
            if (line.display_type === "line_section" || line.display_type === "line_note") continue;
            if (line.is_tip) continue;
            const pid = line.product_id?.[0];
            if (!pid) continue;

            const tmplId = tmplIdByProductId[pid];
            const p = tmplId ? tmplById[tmplId] : null;
            if (!p) continue;

            if (!firstCategId && p.categ_id?.[0]) firstCategId = p.categ_id[0];

            const cartItemId = Date.now() + idx;
            idx += 1;

            const startParts = odooDatetimeToLocalParts(line.start_date);
            const endParts = odooDatetimeToLocalParts(line.return_date);
            const hasRentalSlot = !!(line.start_date && line.return_date);
            const isAddon = line.is_rental && !hasRentalSlot;

            const listP = p.list_price || 0;
            const pickP = p.pick_up_price || 0;
            const dropP = p.drop_off_price || 0;
            const pu = line.price_unit || 0;
            let priceType = "staffed";
            if (Math.abs(pu - pickP) < 0.015) priceType = "pickup";
            else if (Math.abs(pu - dropP) < 0.015) priceType = "dropoff";
            else if (Math.abs(pu - listP) < 0.015) priceType = "staffed";

            pricingSelections[cartItemId] = priceType;

            cart.push({
                id: cartItemId,
                productId: p.id,
                parentProductId: p.id,
                name: p.name,
                image_128: p.image_128,
                default_code: p.default_code,
                list_price: p.list_price,
                pick_up_price: p.pick_up_price,
                drop_off_price: p.drop_off_price,
                date: isAddon ? "" : startParts.date,
                startTime: isAddon ? "" : startParts.time,
                endTime: isAddon ? "" : endParts.time,
                isAddon,
                per_hour_rate: p.per_hour_rate || 0,
                minimum_booking_hrs: p.minimum_booking_hrs || 0,
                base_hrs: p.base_hrs || 0,
                qty: line.product_uom_qty || 1,
                customPrice: pu,
            });
        }

        this.state.cart = cart;
        this.state.pricingSelections = pricingSelections;
        if (firstCategId) {
            this.state.selectedCategoryId = firstCategId;
            this.state.selectedCategoryName = "";
        }
        this.state.existingPosOrderId = orderId;
        this.state.createdOrderId = null;
        this.state.page = ["payment", "checkout", "pricing", "products"].includes(targetPage) ? targetPage : "payment";

        this._recomputeEventIsInPast();
        const evtLat = this.state.event.latitude;
        const evtLng = this.state.event.longitude;
        if (evtLat != null && evtLng != null) {
            await this._applyTravelFee(evtLat, evtLng);
        }
        this.saveState();
    }

    /**
     * Inspect all customer invoices/refunds linked to the loaded sale order (down payments + full, etc.)
     * and set existingOrderPaymentBanner for the UI.
     */
    async refreshExistingOrderPaymentBanner() {
        if (!this.state.existingPosOrderId) {
            this.state.existingOrderPaymentBanner = null;
            return;
        }
        const oid = this.state.existingPosOrderId;
        try {
            const [so] = await this.orm.read("sale.order", [oid], ["invoice_ids", "currency_id"]);
            let sym = "$";
            if (so.currency_id?.[0]) {
                const [cur] = await this.orm.read("res.currency", [so.currency_id[0]], ["symbol"]);
                if (cur?.symbol) sym = cur.symbol;
            }

            const invIds = so.invoice_ids || [];
            if (!invIds.length) {
                this.state.existingOrderPaymentBanner = {
                    variant: "info",
                    lines: ["No customer invoices linked to this order yet."],
                };
                return;
            }

            const moves = await this.orm.read("account.move", invIds, [
                "move_type", "state", "amount_residual", "payment_state", "name",
            ]);

            const receivable = moves.filter(m => ["out_invoice", "out_refund"].includes(m.move_type));
            const drafts = receivable.filter(m => m.state === "draft");
            const posted = receivable.filter(m => m.state === "posted");

            const isPostedPaid = m => {
                if (["paid", "reversed"].includes(m.payment_state)) return true;
                return Math.abs(m.amount_residual || 0) < 0.01;
            };

            const unpaidPosted = posted.filter(m => !isPostedPaid(m));

            const lines = [];
            let variant = "info";

            if (unpaidPosted.length) {
                variant = "warning";
                const unpaidInv = unpaidPosted.filter(m => m.move_type === "out_invoice");
                const unpaidRef = unpaidPosted.filter(m => m.move_type === "out_refund");
                let totalResidual = 0;
                for (const m of unpaidInv) {
                    totalResidual += m.amount_residual || 0;
                }
                const types = unpaidPosted.map(m => m.payment_state).filter(Boolean);
                const partial = types.some(t => t === "partial" || t === "in_payment");
                if (unpaidInv.length) {
                    lines.push(
                        `Outstanding balance: ${sym}${this.fmt(totalResidual)} — ${unpaidInv.length} posted invoice(s) not fully paid` +
                        (partial ? " (partial or in payment)." : ".")
                    );
                }
                if (unpaidRef.length) {
                    lines.push(
                        `${unpaidRef.length} credit note(s) not fully reconciled — review in Accounting.`
                    );
                }
                if (drafts.length) {
                    lines.push(`${drafts.length} draft invoice(s) — not posted yet.`);
                }
            } else if (posted.length) {
                variant = "success";
                lines.push("Order Done - Fully Paid");
                if (drafts.length) {
                    variant = "warning";
                    lines.push(
                        `All posted invoices are paid. ${drafts.length} draft invoice(s) still open — post or delete them to clear this warning.`
                    );
                }
            } else if (drafts.length) {
                variant = "warning";
                lines.push(
                    `${drafts.length} invoice(s) in draft only — post them before payment can be recorded.`
                );
            } else {
                this.state.existingOrderPaymentBanner = {
                    variant: "info",
                    lines: ["No posted or draft customer invoices found for this order."],
                };
                return;
            }

            this.state.existingOrderPaymentBanner = { variant, lines };
        } catch (e) {
            console.error("[RentalPOS] refreshExistingOrderPaymentBanner failed", e);
            this.state.existingOrderPaymentBanner = {
                variant: "warning",
                lines: ["Could not load invoice payment status. Check Accounting ▸ Invoices."],
            };
        }
    }

    // ── PRODUCTS ──────────────────────────────────────────────────────────────

    async loadProducts() {
        this.state.loading = true;
        try {
            const domain = [];
            if (this.state.selectedCategoryId) {
                domain.push(["categ_id", "=", this.state.selectedCategoryId]);
            }
            const products = await this.orm.searchRead(
                "product.template",
                domain,
                ["id", "name", "list_price", "pick_up_price", "drop_off_price",
                    "default_code", "image_128", "categ_id",
                    "per_hour_rate", "minimum_booking_hrs", "base_hrs"],
                { order: "name asc", limit: 200 }
            );
            this.state.products = products;
        } catch (e) {
            console.error("Failed to load products", e);
        } finally {
            this.state.loading = false;
        }
    }

    // ── INLINE CARD EXPAND ────────────────────────────────────────────────────

    toggleExpand(product) {
        if (this.state.expandedCard === product.id) {
            this.state.expandedCard = null;
            this.state.expandedDate = this.state.expandedStartTime = this.state.expandedEndTime = "";
        } else {
            this.state.expandedCard = product.id;
            this.state.expandedDate = this.state.expandedStartTime = this.state.expandedEndTime = "";
        }
    }

    _recomputeEventIsInPast() {
        const now = new Date();
        const main = this.state.cart.find(i => !i.isAddon && i.date && i.startTime);
        if (!main) {
            this.state.eventIsInPast = false;
            return;
        }
        const dt = new Date(`${main.date}T${main.startTime}:00`);
        this.state.eventIsInPast = dt < now;
    }

    // ── CART ──────────────────────────────────────────────────────────────────

    async addToCart(product) {
        if (!this.state.expandedDate || !this.state.expandedStartTime || !this.state.expandedEndTime) {
            alert("Please fill in date, start time, and end time.");
            return;
        }

        // Minimum booking hours validation
        if (product.minimum_booking_hrs > 0) {
            const hours = this.getDurationHours(
                this.state.expandedDate,
                this.state.expandedStartTime,
                this.state.expandedEndTime
            );
            if (hours < product.minimum_booking_hrs) {
                alert(`This product requires a minimum booking of ${product.minimum_booking_hrs} hour(s). Please adjust your end time.`);
                return;
            }
        }

        // Increment order number when adding first line to an empty cart
        if (!this.state.cart.length) {
            this.state.orderSequence = (this.state.orderSequence || 0) + 1;
            this.state.currentOrderNumber = this.state.orderSequence;
        }

        const cartItemId = Date.now();
        this.state.cart = [...this.state.cart, {
            id: cartItemId,
            productId: product.id,
            parentProductId: product.id,
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
            per_hour_rate: product.per_hour_rate || 0,
            minimum_booking_hrs: product.minimum_booking_hrs || 0,
            base_hrs: product.base_hrs || 0,
            qty: 1,               // ← inline qty editing
            customPrice: undefined, // ← inline price override (undefined = use auto)
        }];
        this.state.pricingSelections = { ...this.state.pricingSelections, [cartItemId]: "staffed" };
        this.state.expandedCard = null;
        this.state.expandedDate = this.state.expandedStartTime = this.state.expandedEndTime = "";

        this.state.page = "pricing";
        this._recomputeEventIsInPast();
        this.saveState();
        await this._loadAddons();
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
            date: "", startTime: "", endTime: "",
            isAddon: true,
            qty: 1,               // ← inline qty editing
            customPrice: undefined, // ← inline price override
        }];
        this.state.pricingSelections = { ...this.state.pricingSelections, [cartItemId]: "staffed" };
        this._recomputeEventIsInPast();
        this.saveState();
    }

    removeFromCart(itemId) {
        this.state.cart = this.state.cart.filter(i => i.id !== itemId);
        const updated = { ...this.state.pricingSelections };
        delete updated[itemId];
        this.state.pricingSelections = updated;
        this._recomputeEventIsInPast();
        this.saveState();
    }

    onItemPriceChange(ev) {
        const native = ev.originalEvent || ev;
        const input = native.target || native.currentTarget;
        const itemId = parseInt(input.dataset.itemId);
        this.setItemCustomPrice(itemId, parseFloat(input.value) || 0);
    }

    onItemQtyChange(ev) {
        const native = ev.originalEvent || ev;
        const input = native.target || native.currentTarget;
        const itemId = parseInt(input.dataset.itemId);
        this.setItemQty(itemId, parseInt(input.value) || 1);
    }
    setItemCustomPrice(itemId, price) {
        this.state.cart = this.state.cart.map(i =>
            i.id === itemId ? { ...i, customPrice: price } : i
        );
        this.saveState();
    }

    /** Set quantity (minimum 1) for a single cart item. */
    setItemQty(itemId, qty) {
        this.state.cart = this.state.cart.map(i =>
            i.id === itemId ? { ...i, qty: Math.max(1, qty) } : i
        );
        this.saveState();
    }

    // ── ADDONS ────────────────────────────────────────────────────────────────

    _parseWebflowIdList(raw) {
        if (raw == null || raw === "") return [];
        if (Array.isArray(raw)) return raw.filter(Boolean).map(String);
        if (typeof raw !== "string") return [];
        try {
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed.filter(Boolean).map(String) : [];
        } catch {
            return [];
        }
    }

    async _loadAddons() {
        if (this.state.addonsLoading) return;
        this.state.addonsLoading = true;
        try {
            const productIds = [...new Set(
                this.state.cart.filter(i => !i.isAddon).map(i => i.parentProductId || i.productId)
            )];
            if (!productIds.length) {
                this.state.addonProducts = [];
                return;
            }
            const templates = await this.orm.searchRead(
                "product.template",
                [["id", "in", productIds]],
                ["id", "categ_id", "webflow_item_id"]
            );
            const categIds = [...new Set(
                templates.map(t => t.categ_id && t.categ_id[0]).filter(Boolean)
            )];
            if (!categIds.length) {
                this.state.addonProducts = [];
                return;
            }
            const categories = await this.orm.searchRead(
                "product.category",
                [["id", "in", categIds]],
                ["id", "webflow_addons", "webflow_prods_2023"]
            );
            const categById = Object.fromEntries(categories.map(c => [c.id, c]));
            const addonWfIds = new Set();

            for (const tmpl of templates) {
                const cid = tmpl.categ_id && tmpl.categ_id[0];
                if (!cid) continue;
                const cat = categById[cid];
                if (!cat) continue;

                const allowedMain = this._parseWebflowIdList(cat.webflow_prods_2023);
                const wfMain = tmpl.webflow_item_id ? String(tmpl.webflow_item_id) : "";
                if (allowedMain.length) {
                    if (!wfMain || !allowedMain.includes(wfMain)) continue;
                }

                for (const aid of this._parseWebflowIdList(cat.webflow_addons)) {
                    addonWfIds.add(aid);
                }
            }

            const ids = [...addonWfIds];
            if (!ids.length) {
                this.state.addonProducts = [];
                return;
            }
            this.state.addonProducts = await this.orm.searchRead(
                "product.template",
                [["webflow_item_id", "in", ids]],
                ["id", "name", "list_price", "pick_up_price", "drop_off_price",
                    "default_code", "image_128", "webflow_item_id"]
            );
        } catch (e) {
            console.error("Failed to load addons", e);
        } finally {
            this.state.addonsLoading = false;
        }
    }

    // ── NAVIGATION ────────────────────────────────────────────────────────────

    goBack() {
        if (this.state.page === "checkout") { this.state.page = "pricing"; }
        else if (this.state.page === "pricing") { this.state.page = "products"; this.state.expandedCard = null; this.state.addonProducts = []; }
        else { this.state.page = "products"; this.state.expandedCard = null; }
        this.saveState();
    }

    goBackToCart() {
        this.state.page = "pricing";
        this.saveState();
    }

    goBackToCheckout() {
        if (this.state.page !== "payment") return;
        this.state.page = "checkout";
        this.saveState();
    }

    isCheckoutValid() {
        if (!this.state.cart.length) return false;
        const b = this.state.billing;
        if (!b.firstName || !b.lastName || !b.email || !b.phone) return false;
        if (!b.address || !b.zip || !b.city || !b.state) return false;
        return true;
    }

    async goToPaymentPage() {
        this.state.page = "payment";
        this.saveState();
        if (this.state.existingPosOrderId) {
            await this.refreshExistingOrderPaymentBanner();
        }
    }

    async goToPricing() {
        if (!this.state.cart.length) { alert("Your cart is empty."); return; }
        this.state.page = "pricing";
        this.saveState();
        await this._loadAddons();
    }
    goToCheckout() { this.state.page = "checkout"; this.saveState(); }
    continueShopping() { this.state.page = "products"; this.state.expandedCard = null; this.state.addonProducts = []; this.saveState(); }

    resetOrder() {
        this.state.cart = [];
        this.state.pricingSelections = {};
        this.state.addonProducts = [];
        this.state.travelFeeInfo = null;
        this.state.expandedCard = null;
        this.state.eventIsInPast = false;
        this.saveState();
    }

    /** Always calculate travel fee from event address coordinates. */
    _applyTravelFeeFromEventCoords() {
        const lat = this.state.event.latitude;
        const lng = this.state.event.longitude;
        if (lat != null && lng != null) {
            this._applyTravelFee(lat, lng);
        } else if (this._isAllPickup()) {
            this.state.additional = { ...this.state.additional, overrideTravelFee: 0 };
            this.state.travelFeeInfo = null;
        }
    }

    setPriceType(itemId, type) {
        this.state.cart = this.state.cart.map(i =>
            i.id === itemId ? { ...i, customPrice: undefined } : i
        );
        this.state.pricingSelections = { ...this.state.pricingSelections, [itemId]: type };
        this.saveState();
        // Re-evaluate travel fee using event address: pickup-only = no fee, otherwise recalculate
        this._applyTravelFeeFromEventCoords();
    }

    getDurationHours(date, startTime, endTime) {
        if (!date || !startTime || !endTime) return 1;
        try {
            const [sh, sm] = startTime.split(":").map(Number);
            const [eh, em] = endTime.split(":").map(Number);
            let s = sh * 60 + sm, e = eh * 60 + em;
            if (e <= s) e += 24 * 60;
            return Math.max(1, (e - s) / 60);
        } catch { return 1; }
    }

    getExtraTimeCharge(date, startTime, endTime, freeHrs = 1) {
        if (!date || !startTime || !endTime) return 0;
        const freeBlocks = Math.round(freeHrs * 4); // 4 blocks per hour (15-min each)
        const totalBlocks = Math.ceil(this.getDurationHours(date, startTime, endTime) * 60 / 15);
        const billableBlocks = Math.max(0, totalBlocks - freeBlocks);
        return billableBlocks * 25;
    }

    /**
     * Returns the UNIT price for a cart item.
     * - If the user set a customPrice it always wins.
     * - Otherwise the price is derived from the pricing type + extra time charge.
     *
     * Cases (staffed only — pickup/dropoff always return base price):
     *   A) base_hrs=0, per_hour_rate=0 → 1 hr free, then $25/15 min
     *   B) base_hrs=0, per_hour_rate>0 → 1 hr free, then ceil(extra hrs) × per_hour_rate
     *   C) base_hrs>0, per_hour_rate>0 → base_hrs free, then proportional per_hour_rate on excess
     *   D) base_hrs>0, per_hour_rate=0 → base_hrs free, then $25/15 min on excess
     */
    getItemPrice(item) {
        if (item.customPrice !== undefined) return item.customPrice;

        const type = this.state.pricingSelections[item.id] || "staffed";
        let p = 0;
        if (type === "staffed") p = item.list_price || 0;
        if (type === "pickup") p = item.pick_up_price || 0;
        if (type === "dropoff") p = item.drop_off_price || 0;
        if (item.isAddon || !item.date || !item.startTime || !item.endTime) return p;
        if (type !== "staffed") return p;

        const hours       = this.getDurationHours(item.date, item.startTime, item.endTime);
        const baseHrs     = item.base_hrs > 0 ? item.base_hrs : 0;
        const perHourRate = item.per_hour_rate > 0 ? item.per_hour_rate : 0;

        if (baseHrs > 0) {
            // Cases C & D: standard price covers baseHrs
            const excessHrs = Math.max(0, hours - baseHrs);
            if (excessHrs === 0) return p;
            if (perHourRate > 0) {
                // Case C: proportional per_hour_rate on excess (e.g. 30 min @ $200/hr = $100)
                return p + Math.round(excessHrs * perHourRate * 100) / 100;
            }
            // Case D: $25/15 min on excess
            return p + this.getExtraTimeCharge(item.date, item.startTime, item.endTime, baseHrs);
        }

        if (perHourRate > 0) {
            // Case B: 1 hr free, ceil(extra hours) × per_hour_rate
            const extraHours = Math.max(0, Math.ceil(hours) - 1);
            return p + extraHours * perHourRate;
        }

        // Case A: 1 hr free, then $25/15 min
        return p + this.getExtraTimeCharge(item.date, item.startTime, item.endTime, 1);
    }

    /** Line total = unit price × qty. */
    getItemLineTotal(item) {
        return this.getItemPrice(item) * (item.qty || 1);
    }

    getItemDurationLabel(item) {
        if (item.isAddon || !item.date || !item.startTime || !item.endTime) return "";
        const hours       = this.getDurationHours(item.date, item.startTime, item.endTime);
        const type        = this.state.pricingSelections[item.id] || "staffed";
        const fmt         = h => h % 1 === 0 ? `${h}` : h.toFixed(2);

        if (type !== "staffed") return `${fmt(hours)} hrs`;

        const baseHrs     = item.base_hrs > 0 ? item.base_hrs : 0;
        const perHourRate = item.per_hour_rate > 0 ? item.per_hour_rate : 0;

        if (baseHrs > 0) {
            const excessHrs = Math.max(0, hours - baseHrs);
            if (excessHrs === 0) {
                return `${fmt(hours)} hrs (within ${fmt(baseHrs)} hr base, no extra charge)`;
            }
            if (perHourRate > 0) {
                // Case C: proportional per_hour_rate on excess
                const extra = Math.round(excessHrs * perHourRate * 100) / 100;
                return `${fmt(hours)} hrs (+$${extra} @ $${perHourRate}/hr over ${fmt(baseHrs)} hr base)`;
            }
            // Case D: $25/15 min on excess
            const extra = this.getExtraTimeCharge(item.date, item.startTime, item.endTime, baseHrs);
            return `${fmt(hours)} hrs (+$${extra} time charge, ${fmt(baseHrs)} hr base included)`;
        }

        if (perHourRate > 0) {
            // Case B: ceil extra hours × per_hour_rate (1 hr free)
            const extraHours = Math.max(0, Math.ceil(hours) - 1);
            const extra = extraHours * perHourRate;
            return `${fmt(hours)} hrs (+$${extra} @ $${perHourRate}/hr)`;
        }

        // Case A: $25/15 min after 1 hr free
        const extra = this.getExtraTimeCharge(item.date, item.startTime, item.endTime, 1);
        return extra > 0
            ? `${fmt(hours)} hrs (+$${extra} time charge)`
            : `${fmt(hours)} hrs`;
    }

    /** Cart subtotal = sum of all line totals (price × qty). */
    getCartTotal() {
        return this.state.cart.reduce((s, i) => s + this.getItemLineTotal(i), 0);
    }

    getDiscountAmount() {
        if (!this.state.additional.discountApplied) return 0;
        const val = this.state.additional.generalDiscount || 0;
        if (this.state.additional.discountType === "amount") {
            return Math.min(val, this.getCartTotal());
        }
        return this.getCartTotal() * (val / 100);
    }

    getEffectiveTax() {
        const sub = this.getCartTotal();
        const disc = this.getDiscountAmount();
        const coup = this.state.additional.couponDiscount || 0;
        const waiver = this.getDamageWaiverAmount();
        const evtFee = this.getEventLocationFee();
        const surfaceFee = this.getSetupSurfaceFee();
        const taxableAmount = Math.max(0, sub - disc - coup + waiver + evtFee + surfaceFee);

        const taxPct = this.getAppliedTaxPercent();
        return Math.round(taxableAmount * (taxPct / 100) * 100) / 100;
    }

    getDepositAmount() {
        const pct = this.state.additional.depositPercent || 0;
        if (pct <= 0) return 0;
        const sub = this.getCartTotal(), disc = this.getDiscountAmount();
        const coup = this.state.additional.couponDiscount || 0;
        const misc = this.state.additional.miscellaneousFees || 0;
        const travel = this.state.additional.overrideTravelFee || 0;
        const waiver = this.getDamageWaiverAmount();
        const evtFee = this.getEventLocationFee();
        const surfaceFee = this.getSetupSurfaceFee();
        return (sub - disc - coup + misc + travel + waiver + evtFee + surfaceFee + this.getEffectiveTax()) * (pct / 100);
    }

    getCheckoutGrandTotal() {
        const sub = this.getCartTotal();
        const disc = this.getDiscountAmount();
        const coup = this.state.additional.couponDiscount || 0;
        const misc = this.state.additional.miscellaneousFees || 0;
        const travel = this.state.additional.overrideTravelFee || 0;
        const waiver = this.getDamageWaiverAmount();
        const evtFee = this.getEventLocationFee();
        const surfaceFee = this.getSetupSurfaceFee();
        return Math.max(0, sub - disc - coup + misc + travel + waiver + evtFee + surfaceFee + this.getEffectiveTax());
    }

    getGrandTotal() {
        const taxPct = this.getAppliedTaxPercent();
        return this.getCartTotal() * (1 + taxPct / 100);
    }

    getAppliedTaxPercent() {
        const override = this.state.additional.overrideTaxAmount;
        if (override !== null && override !== undefined && override !== "") {
            const parsed = parseFloat(override);
            if (!Number.isNaN(parsed)) return parsed;
        }
        const pct = this.state.companySalesTax.amount || 0;
        if (!pct) {
            console.warn("[RentalPOS][TAX] applied tax is 0%", {
                overrideTaxAmount: this.state.additional.overrideTaxAmount,
                companySalesTax: this.state.companySalesTax,
            });
        }
        return pct;
    }

    getDamageWaiverAmount() {
        if (this.state.event?.damageWaiver !== "yes") return 0;
        return Math.round(this.getCartTotal() * 0.10 * 100) / 100;
    }

    getEventLocationFee() {
        return this.state.event?.eventLocation === "yes_20" ? 20 : 0;
    }

    getSetupSurfaceFee() {
        const fees = {
            asphalt_35: 35,
            concrete_35: 35,
            turf_35: 35,
            drive_in_movie_asphalt_100: 100,
        };
        return fees[this.state.additional?.setupSurface] || 0;
    }

    getSetupSurfaceLabel() {
        const labels = {
            asphalt_35: 'Asphalt',
            concrete_35: 'Concrete',
            turf_35: 'Turf',
            drive_in_movie_asphalt_100: 'Drive In Movie Asphalt',
        };
        return labels[this.state.additional?.setupSurface] || '';
    }

    // ── CUSTOMER ──────────────────────────────────────────────────────────────

    async searchCustomers(query) {
        if (!query || query.length < 2) { this.state.customerResults = []; return; }
        this.state.customerSearchLoading = true;
        try {
            this.state.customerResults = await this.orm.searchRead(
                "res.partner",
                ["|", ["name", "ilike", query], ["email", "ilike", query]],
                ["id", "name", "email", "phone", "phone_secondary",
                    "company_name", "street", "zip", "city", "state_id",
                    "partner_latitude", "partner_longitude"],
                { limit: 10 }
            );
        } catch (e) { console.error("Customer search failed", e); }
        finally { this.state.customerSearchLoading = false; }
    }

    selectCustomer(partner) {
        const nameParts = (partner.name || "").split(" ");
        const lat = partner.partner_latitude || null;
        const lng = partner.partner_longitude || null;

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
            latitude: lat, longitude: lng,
        };
        this.state.billingAddressRaw = partner.street || "";
        this.state.showBillingSuggestions = false;
        this.state.showCustomerDialog = false;
        this.state.customerSearch = "";
        this.state.customerResults = [];

        // Travel fee is based on event address; only sync if event mirrors billing
        if (this.state.event.sameAsBilling) {
            this.state.event = {
                ...this.state.event,
                address: partner.street || "",
                city: partner.city || "",
                state: partner.state_id ? partner.state_id[1] : "",
                zip: partner.zip || "",
                latitude: lat,
                longitude: lng,
            };
            this.state.eventAddressRaw = partner.street || "";
            if (lat && lng) this._applyTravelFee(lat, lng);
        }
    }

    setBillingField(field, value) {
        this.state.billing = { ...this.state.billing, [field]: value };
        this._schedulePartnerSave();
    }

    _schedulePartnerSave() {
        if (this._partnerSaveTimer) clearTimeout(this._partnerSaveTimer);
        this._partnerSaveTimer = setTimeout(() => {
            this._partnerSaveTimer = null;
            this._autoSavePartner();
        }, 800);
    }

    async _autoSavePartner() {
        const b = this.state.billing;
        const fullName = `${b.firstName} ${b.lastName}`.trim();

        if (b.selectedPartnerId) {
            // Existing partner — write all editable fields back immediately
            const vals = {
                email: b.email || false,
                phone: b.phone || false,
                phone_secondary: b.secondaryPhone || false,
                street: b.address || false,
                zip: b.zip || false,
                city: b.city || false,
                company_name: b.company || false,
            };
            if (fullName) vals.name = fullName;
            if (b.latitude !== null) vals.partner_latitude = b.latitude;
            if (b.longitude !== null) vals.partner_longitude = b.longitude;
            try {
                await this.orm.write("res.partner", [b.selectedPartnerId], vals);
            } catch (e) { console.error("Auto-save partner failed", e); }
        } else if (fullName) {
            // New customer — create the partner now so subsequent edits update it
            const vals = {
                name: fullName,
                email: b.email || false,
                phone: b.phone || false,
                phone_secondary: b.secondaryPhone || false,
                street: b.address || false,
                zip: b.zip || false,
                city: b.city || false,
                company_name: b.company || false,
            };
            if (b.latitude !== null) vals.partner_latitude = b.latitude;
            if (b.longitude !== null) vals.partner_longitude = b.longitude;
            try {
                const result = await this.orm.create("res.partner", [vals]);
                const newId = Array.isArray(result) ? result[0] : result;
                this.state.billing = { ...this.state.billing, selectedPartnerId: newId };
            } catch (e) { console.error("Auto-create partner failed", e); }
        }
    }

    // ── ACCORDION ─────────────────────────────────────────────────────────────

    setAccordion(name) { this.state.activeAccordion = this.state.activeAccordion === name ? null : name; }

    // ── EVENT ─────────────────────────────────────────────────────────────────

    setEventField(field, value) { this.state.event = { ...this.state.event, [field]: value }; }

    onStillDeliverChange(e) {
        const checked = e.target.checked;
        this.state.event = { ...this.state.event, stillDeliver: checked };
        // Trigger travel fee calculation from event coords when user opts to still deliver
        if (checked) {
            this._applyTravelFeeFromEventCoords();
        }
    }

    async toggleSameAsBilling(checked) {
        this.state.event.sameAsBilling = checked;
        if (checked) {
            this.state.event.address = this.state.billing.address;
            this.state.event.city = this.state.billing.city;
            this.state.event.state = this.state.billing.state;
            this.state.event.zip = this.state.billing.zip;
            this.state.event.latitude = this.state.billing.latitude;
            this.state.event.longitude = this.state.billing.longitude;
            this.state.eventAddressRaw = this.state.billing.address;
            this.state.showEventSuggestions = false;
            await this.verifyEventZip(this.state.billing.zip);
            // Recalculate travel fee now that event coords match billing
            if (this.state.billing.latitude != null && this.state.billing.longitude != null) {
                await this._applyTravelFee(this.state.billing.latitude, this.state.billing.longitude);
            }
        } else {
            this.state.event.zipStatus = null;
            this.state.event.zipRecord = null;
            this.state.event.latitude = null;
            this.state.event.longitude = null;
            this.state.eventAddressRaw = "";
            this.state.event.stillDeliver = false;
        }
    }

    async verifyEventZip(zip) {
        if (!zip || zip.length < 3) { this.state.event.zipStatus = null; return; }
        try {
            const activeCompanyId = await this._getActiveCompanyId();
            const domain = [["name", "=", zip]];
            if (activeCompanyId) domain.push(["company_id", "=", activeCompanyId]);
            const result = await this.orm.searchRead(
                "rental.zipcode", domain,
                ["id", "name", "city", "state_id"], { limit: 1 }
            );
            this.state.event.zipStatus = result.length ? "available" : "not_available";
            this.state.event.zipRecord = result[0] || null;
        } catch (e) { console.error("Zip verification failed", e); }
    }

    // ── ADDITIONAL ────────────────────────────────────────────────────────────

    setAdditionalField(field, value) { this.state.additional = { ...this.state.additional, [field]: value }; }

    applyDiscount() {
        const val = this.state.additional.generalDiscount;
        if (!val || val <= 0) return;
        this.state.additional.discountApplied = true;
    }

    onDiscountChange(e) {
        const v = parseFloat(e.target.value) || 0;
        this.setAdditionalField('generalDiscount', v);
        this.setAdditionalField('discountApplied', false);
    }
    onDepositPercentChange(e) { this.setAdditionalField('depositPercent', parseFloat(e.target.value) || 0); }
    onOverrideTaxChange(e) {
        const raw = String(e.target.value ?? "").trim();
        if (raw === "") {
            this.setAdditionalField('overrideTaxAmount', null);
            return;
        }
        const parsed = parseFloat(raw);
        this.setAdditionalField('overrideTaxAmount', Number.isNaN(parsed) ? null : parsed);
    }
    onMiscFeesChange(e) { this.setAdditionalField('miscellaneousFees', parseFloat(e.target.value) || 0); }

    onOverrideTravelFeeChange(e) {
        this.setAdditionalField('overrideTravelFee', parseFloat(e.target.value) || 0);
        this.state.travelFeeInfo = null;
    }

    async applyCoupon() {
        const code = this.state.additional.couponCode;
        if (!code) { alert("Please enter a coupon code."); return; }
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
            if (card.expiration_date && new Date(card.expiration_date) < new Date()) {
                this.state.additional.couponApplied = false;
                this.state.additional.couponDiscount = 0;
                this.state.additional.couponError = "This coupon has expired.";
                return;
            }
            const rewards = await this.orm.searchRead(
                "loyalty.reward",
                [["program_id", "=", card.program_id[0]], ["reward_type", "=", "discount"]],
                ["id", "discount", "discount_mode", "discount_max_amount", "reward_type"],
                { limit: 1 }
            );
            if (!rewards.length) {
                this.state.additional.couponApplied = false;
                this.state.additional.couponDiscount = 0;
                this.state.additional.couponError = "No discount reward found.";
                return;
            }
            const reward = rewards[0];
            let disc = reward.discount_mode === "percent"
                ? Math.min(
                    this.getCartTotal() * (reward.discount / 100),
                    reward.discount_max_amount > 0 ? reward.discount_max_amount : Infinity
                )
                : reward.discount_mode === "per_point"
                    ? card.points * reward.discount
                    : reward.discount;
            this.state.additional.couponApplied = true;
            this.state.additional.couponDiscount = disc;
            this.state.additional.couponError = "";
            this.state.additional.couponLabel = `${card.program_id[1]} (${reward.discount_mode === "percent" ? reward.discount + "%" : "$" + reward.discount})`;
        } catch (e) {
            console.error("Coupon lookup failed", e);
            this.state.additional.couponError = "Failed to verify coupon.";
        }
    }

    // ── MAPBOX ADDRESS AUTOCOMPLETE ───────────────────────────────────────────

    onBillingAddressInput(e) {
        const val = e.target.value;
        this.state.billingAddressRaw = val;
        this.state.billing = { ...this.state.billing, address: val };
        if (val.length < 3) { this.state.showBillingSuggestions = false; this.state.billingSuggestions = []; return; }
        this._debouncedBillingSuggest(val);
    }

    async selectBillingSuggestion(suggestion) {
        this.state.showBillingSuggestions = false;
        this.state.billingSuggestions = [];

        const props = await mapboxRetrieve(suggestion.mapbox_id, this._billingSessionToken);
        this._billingSessionToken = newSessionToken();
        if (!props) return;

        const addr = parseMapboxFeature(props);
        const street = addr.street || suggestion.address || "";

        this.state.billing = {
            ...this.state.billing,
            address: street, city: addr.city, state: addr.state, zip: addr.zip,
            latitude: addr.latitude, longitude: addr.longitude,
        };
        this.state.billingAddressRaw = street;

        if (this.state.billing.selectedPartnerId) {
            try {
                const wv = { street, city: addr.city || "", zip: addr.zip || "" };
                if (addr.latitude !== null) wv.partner_latitude = addr.latitude;
                if (addr.longitude !== null) wv.partner_longitude = addr.longitude;
                await this.orm.write("res.partner", [this.state.billing.selectedPartnerId], wv);
            } catch (e) { console.error("Failed to update partner address/coordinates", e); }
        }

        // Travel fee is based on event address; only sync if event mirrors billing
        if (this.state.event.sameAsBilling) {
            this.state.event = {
                ...this.state.event,
                address: street,
                city: addr.city,
                state: addr.state,
                zip: addr.zip,
                latitude: addr.latitude,
                longitude: addr.longitude,
            };
            this.state.eventAddressRaw = street;
            if (addr.latitude !== null && addr.longitude !== null) {
                this._applyTravelFee(addr.latitude, addr.longitude);
            }
        }
    }

    onBillingAddressBlur() { setTimeout(() => { this.state.showBillingSuggestions = false; }, 200); }

    onEventAddressInput(e) {
        const val = e.target.value;
        this.state.eventAddressRaw = val;
        this.state.event = { ...this.state.event, address: val };
        if (val.length < 3) { this.state.showEventSuggestions = false; this.state.eventSuggestions = []; return; }
        this._debouncedEventSuggest(val);
    }

    async selectEventSuggestion(suggestion) {
        this.state.showEventSuggestions = false;
        this.state.eventSuggestions = [];

        const props = await mapboxRetrieve(suggestion.mapbox_id, this._eventSessionToken);
        this._eventSessionToken = newSessionToken();
        if (!props) return;

        const addr = parseMapboxFeature(props);
        const street = addr.street || suggestion.address || "";

        this.state.event = {
            ...this.state.event,
            address: street, city: addr.city, state: addr.state, zip: addr.zip,
            latitude: addr.latitude, longitude: addr.longitude,
        };
        this.state.eventAddressRaw = street;
        await this.verifyEventZip(addr.zip);

        // Recalculate travel fee from the new event address
        if (addr.latitude !== null && addr.longitude !== null) {
            this._applyTravelFee(addr.latitude, addr.longitude);
        }

        if (this.state.createdOrderId) {
            try {
                const wv = { event_street: street, event_city: addr.city || "", event_zip: addr.zip || "" };
                if (addr.latitude !== null) wv.event_latitude = addr.latitude;
                if (addr.longitude !== null) wv.event_longitude = addr.longitude;
                await this.orm.write("sale.order", [this.state.createdOrderId], wv);
            } catch (e) { console.error("Failed to update order event address/coordinates", e); }
        }
    }

    onEventAddressBlur() { setTimeout(() => { this.state.showEventSuggestions = false; }, 200); }

    // ── EDIT DATE (bulk-update all non-addon cart items) ──────────────────────

    toggleEditDate() {
        if (!this.state.showEditDate) {
            const first = this.state.cart.find(i => !i.isAddon && i.date);
            this.state.editDateValue = first?.date || this.getTodayDate();
            this.state.editStartTime = first?.startTime || "09:00";
            this.state.editEndTime = first?.endTime || "10:00";
        }
        this.state.showEditDate = !this.state.showEditDate;
    }

    applyEditDate() {
        if (!this.state.editDateValue || !this.state.editStartTime || !this.state.editEndTime) {
            alert("Please fill in date, start time, and end time.");
            return;
        }
        this.state.cart = this.state.cart.map(item => {
            if (item.isAddon) return item;
            return {
                ...item,
                date: this.state.editDateValue,
                startTime: this.state.editStartTime,
                endTime: this.state.editEndTime,
            };
        });
        this.state.showEditDate = false;
        this._recomputeEventIsInPast();
        this.saveState();
    }

    // ── PLACE ORDER (invoice-later flow) ──────────────────────────────────────

    async placeOrder() {
        if (!this.state.additional.weatherPolicyAgreed || !this.state.additional.setupTermsAgreed) {
            alert("Please agree to both policies before placing the order.");
            return;
        }
        // Cancel any pending auto-save to avoid duplicate partner creation
        if (this._partnerSaveTimer) {
            clearTimeout(this._partnerSaveTimer);
            this._partnerSaveTimer = null;
        }
        try {
            this.state.placingOrder = true;

            const fullName = `${this.state.billing.firstName} ${this.state.billing.lastName}`.trim();
            let partnerId = false;

            if (this.state.billing.selectedPartnerId) {
                partnerId = this.state.billing.selectedPartnerId;
                const pv = {
                    street: this.state.billing.address || false,
                    city: this.state.billing.city || false,
                    zip: this.state.billing.zip || false,
                    email: this.state.billing.email || false,
                    phone: this.state.billing.phone || false,
                    phone_secondary: this.state.billing.secondaryPhone || false,
                    company_name: this.state.billing.company || false,
                };
                if (this.state.billing.latitude !== null) pv.partner_latitude = this.state.billing.latitude;
                if (this.state.billing.longitude !== null) pv.partner_longitude = this.state.billing.longitude;
                await this.orm.write("res.partner", [partnerId], pv);
            } else if (fullName) {
                const cv = {
                    name: fullName,
                    email: this.state.billing.email || false,
                    phone: this.state.billing.phone || false,
                    phone_secondary: this.state.billing.secondaryPhone || false,
                    street: this.state.billing.address || false,
                    zip: this.state.billing.zip || false,
                    city: this.state.billing.city || false,
                    company_name: this.state.billing.company || false,
                };
                if (this.state.billing.latitude !== null) cv.partner_latitude = this.state.billing.latitude;
                if (this.state.billing.longitude !== null) cv.partner_longitude = this.state.billing.longitude;
                const cp = await this.orm.create("res.partner", [cv]);
                partnerId = Array.isArray(cp) ? cp[0] : cp;
            }

            const toOdooUTC = (dateStr, timeStr) => {
                if (!dateStr || !timeStr) return false;
                const d = new Date(`${dateStr}T${timeStr}:00`);
                const pad = n => String(n).padStart(2, "0");
                return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:00`;
            };

            const saleTaxId = this.state.companySalesTax.id;

            const orderLines = [];
            for (const item of this.state.cart) {
                const variants = await this.orm.searchRead(
                    "product.product",
                    [["product_tmpl_id", "=", item.productId]],
                    ["id"], { limit: 1 }
                );
                if (!variants.length) continue;

                let startDate = false, endDate = false;
                if (item.date && item.startTime) startDate = toOdooUTC(item.date, item.startTime);
                if (item.date && item.endTime) {
                    const [sh, sm] = (item.startTime || "00:00").split(":").map(Number);
                    const [eh, em] = item.endTime.split(":").map(Number);
                    const endDay = (eh < sh || (eh === sh && em < sm)) ? this._addDays(item.date, 1) : item.date;
                    endDate = toOdooUTC(endDay, item.endTime);
                }

                orderLines.push([0, 0, {
                    product_id: variants[0].id,
                    price_unit: item.customPrice !== undefined ? item.customPrice : this.getItemPrice(item),
                    product_uom_qty: item.qty || 1,
                    is_rental: true,
                    ...(saleTaxId && { tax_ids: [[6, 0, [saleTaxId]]] }),
                    ...(startDate && { start_date: startDate }),
                    ...(endDate && { return_date: endDate }),
                }]);
            }

            const firstItem = this.state.cart.find(i => i.date && i.startTime);
            const orderRentalStart = firstItem ? toOdooUTC(firstItem.date, firstItem.startTime) : false;

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
                ...(this.state.event.latitude !== null && { event_latitude: this.state.event.latitude }),
                ...(this.state.event.longitude !== null && { event_longitude: this.state.event.longitude }),
                additional_weather_policy_agreed: this.state.additional.weatherPolicyAgreed,
                additional_setup_terms_agreed: this.state.additional.setupTermsAgreed,
                setup_surface: this.state.additional.setupSurface || false,
                general_discount: this.state.additional.generalDiscount || 0,
                internal_notes: this.state.additional.internalNotes || false,
                customer_notes: this.state.additional.customerNotes || false,
                override_travel_fee: this.state.additional.overrideTravelFee || 0,
                override_tax_amount: this.state.additional.overrideTaxAmount || 0,
                miscellaneous_fees: this.state.additional.miscellaneousFees || 0,
                override_deposit_amount: this.getDepositAmount(),
                order_line: orderLines,
            };

            const co = await this.orm.create("sale.order", [orderVals], {
                context: { in_rental_app: 1, default_is_rental_order: 1 },
            });
            const orderId = Array.isArray(co) ? co[0] : co;
            this.state.lastDepositPercent = this.state.additional.depositPercent || 0;
            this.state.lastCustomerEmail = this.state.billing.email || "";
            this.state.lastCustomerPartnerId = this.state.billing.selectedPartnerId || false;

            this._resetAfterOrder();
            this.state.createdOrderId = orderId;
            this.state.paidOnSpot = false;

            // Auto-send quote email — order stays as quotation until customer pays
            try {
                this.state.invoiceLoading = true;
                await this.orm.call("sale.order", "action_send_quote_pos", [[orderId]]);
                this.state.invoiceSent = true;
            } catch (e) {
                console.error("Failed to send quote email", e);
                this.state.invoiceError = `Order created but quote email failed: ${e.message || e}`;
            } finally {
                this.state.invoiceLoading = false;
            }

            this.state.page = "success";

        } catch (e) {
            console.error("Failed to place order", e);
            alert(`Failed to create order: ${e.message || e}`);
        } finally {
            this.state.placingOrder = false;
        }
    }

    // ── HELPERS ───────────────────────────────────────────────────────────────

    _addDays(dateStr, days) {
        const d = new Date(dateStr);
        d.setDate(d.getDate() + days);
        return d.toISOString().split("T")[0];
    }

    openCreatedOrder() { window.location.href = `/odoo/rental/${this.state.createdOrderId}`; }

    getImageSrc(product) {
        if (product?.image_128) return `data:image/png;base64,${product.image_128}`;
        return "/web/static/img/placeholder.png";
    }

    getCategoryImageUrl(cat) {
        if (!cat?.webflow_above_the_fold) return null;
        try {
            const data = typeof cat.webflow_above_the_fold === "string"
                ? JSON.parse(cat.webflow_above_the_fold)
                : cat.webflow_above_the_fold;
            return data?.url || null;
        } catch { return null; }
    }

    fmt(val) { return (val || 0).toFixed(2); }

    async createRemainingInvoice() {
        try {
            this.state.invoiceLoading = true;
            this.state.invoiceError = "";
            const remainingPct = 100 - (this.state.lastDepositPercent || 0);
            // deposit_percent: 0 → Odoo creates a full invoice; existing downpayment is deducted automatically
            const invoiceId = await this.orm.call(
                "sale.order",
                "action_create_and_send_invoice_pos",
                [[this.state.createdOrderId]],
                { deposit_percent: 0, flow_type: "remaining", remaining_percent: remainingPct }
            );
            const id = Array.isArray(invoiceId) ? invoiceId[0] : invoiceId;
            this.state.invoiceSent = true;
            this.state.invoiceId = id;
        } catch (e) {
            console.error("Remaining invoice creation failed", e);
            this.state.invoiceError = `Failed: ${e.message || e}`;
        } finally {
            this.state.invoiceLoading = false;
        }
    }

    openInvoice() { window.location.href = `/odoo/accounting/customer-invoices/${this.state.invoiceId}`; }

    getTimeSlots() {
        const slots = [];
        for (let h = 0; h < 24; h++) {
            for (let m = 0; m < 60; m += 30) {
                const hh = String(h).padStart(2, "0"), mm = String(m).padStart(2, "0");
                const dh = h % 12 === 0 ? 12 : h % 12;
                slots.push({ value: `${hh}:${mm}`, label: `${dh}:${mm} ${h < 12 ? "AM" : "PM"}` });
            }
        }
        return slots;
    }

    getTodayDate() { return new Date().toISOString().split("T")[0]; }

    formatEventType(eventType) {
        if (!eventType) return "";
        return eventType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    // ── CATEGORIES ────────────────────────────────────────────────────────────

    async loadCategories() {
        this.state.categoriesLoading = true;
        try {
            const [cats, sections, productPrices, counts] = await Promise.all([
                this.orm.searchRead(
                    "product.category",
                    [],
                    ["id", "name", "complete_name", "parent_id", "section_field", "webflow_above_the_fold"],
                    { order: "complete_name asc" }
                ),
                this.orm.searchRead("rental.section", [], ["id", "name"], { order: "name asc" }),
                this.orm.searchRead(
                    "product.template",
                    [["list_price", ">", 0]],
                    ["categ_id", "list_price"],
                    { limit: 2000 }
                ),
                this.orm.call("product.template", "read_group", [[], ["categ_id"], ["categ_id"]], {}),
            ]);

            const countMap = {};
            counts.forEach(c => {
                if (c.categ_id) countMap[c.categ_id[0]] = c.categ_id_count || 0;
            });

            const minPriceMap = {};
            productPrices.forEach(p => {
                const cid = p.categ_id?.[0];
                if (cid && (minPriceMap[cid] === undefined || p.list_price < minPriceMap[cid])) {
                    minPriceMap[cid] = p.list_price;
                }
            });

            this.state.sections = sections;
            this.state.categories = cats
                .map(c => ({
                    ...c,
                    product_count: countMap[c.id] || 0,
                    min_price: minPriceMap[c.id] ?? null,
                }))
                .filter(c => c.product_count > 0);

        } catch (e) {
            console.error("Failed to load categories", e);
            this.state.categories = [];
        } finally {
            this.state.categoriesLoading = false;
        }
    }

    get filteredCategories() {
        if (!this.state.categories) return [];
        let cats = this.state.categories;
        const term = this.state.categorySearch.toLowerCase();
        if (term) cats = cats.filter(c => c.complete_name.toLowerCase().includes(term));
        if (this.state.selectedSectionId) {
            cats = cats.filter(c => c.section_field && c.section_field[0] === this.state.selectedSectionId);
        }
        return cats;
    }

    get sectionsWithCategories() {
        if (!this.state.sections || !this.state.categories) return [];
        return this.state.sections
            .map(s => ({
                ...s,
                categories: this.state.categories.filter(
                    c => c.section_field && c.section_field[0] === s.id
                ),
            }))
            .filter(s => s.categories.length > 0);
    }

    toggleSectionPanel() {
        this.state.sectionPanelOpen = !this.state.sectionPanelOpen;
    }

    selectSectionFilter(sectionId) {
        this.state.selectedSectionId =
            this.state.selectedSectionId === sectionId ? null : sectionId;
    }

    async selectCategory(cat) {
        this.state.selectedCategoryId = cat.id;
        this.state.selectedCategoryName = cat.name;
        this.state.page = "products";
        await this.loadProducts();
    }

    goToCategories() {
        this.state.page = "categories";
        this.state.selectedCategoryId = null;
        this.state.selectedCategoryName = "";
        this.state.products = [];
        this.state.expandedCard = null;
    }

    // ── PAYMENT ───────────────────────────────────────────────────────────────

    onTogglePayment(e) {
        this.state.payment = { ...this.state.payment, enabled: e.target.checked };
    }

    setPaymentMethod(method) {
        this.state.payment = { ...this.state.payment, method };
    }

    setPaymentSplit(mode) {
        this.state.payment = { ...this.state.payment, splitMode: mode };
    }

    setTipMode(mode) {
        this.state.payment = { ...this.state.payment, tipMode: mode };
    }

    onPaymentCustomPercentChange(e) {
        const v = Math.min(100, Math.max(0, parseFloat(e.target.value) || 0));
        this.state.payment = { ...this.state.payment, customPercent: v };
    }

    onCustomTipChange(e) {
        this.state.payment = { ...this.state.payment, customTip: parseFloat(e.target.value) || 0 };
    }

    onCardNumberInput(e) {
        const raw = String(e.target.value || "").replace(/\D/g, "").slice(0, 19);
        const grouped = raw.replace(/(\d{4})(?=\d)/g, "$1 ").trim();
        this.state.payment = { ...this.state.payment, cardNumber: grouped };
    }

    onCardExpiryInput(e) {
        const raw = String(e.target.value || "").replace(/\D/g, "").slice(0, 4);
        const mm = raw.slice(0, 2);
        const yy = raw.slice(2, 4);
        const val = yy ? `${mm}/${yy}` : mm;
        this.state.payment = { ...this.state.payment, cardExpiry: val };
    }

    onCardCvvInput(e) {
        const cvv = String(e.target.value || "").replace(/\D/g, "").slice(0, 4);
        this.state.payment = { ...this.state.payment, cardCvv: cvv };
    }

    async _iposEnsureFtdLoaded(config) {
        const token = config?.data_token || "";
        const dataSrc = config?.data_src || "";
        const ftdSrc = config?.ftd_src || (dataSrc ? `${dataSrc}/ftd/v1/freedomtodesign.js` : "");
        if (!token || !dataSrc || !ftdSrc) {
            throw new Error("IPOS config missing for FTD tokenization.");
        }

        let script = document.getElementById("ftd");
        if (!script) {
            script = document.createElement("script");
            script.id = "ftd";
            script.async = false;
            script.setAttribute("security_key", token);
            script.setAttribute("data-src", dataSrc);
            script.src = ftdSrc;
            await new Promise((resolve, reject) => {
                script.addEventListener("load", resolve, { once: true });
                script.addEventListener("error", () => reject(new Error("Failed to load FTD script.")), { once: true });
                document.head.appendChild(script);
            });
        } else {
            script.setAttribute("security_key", token);
            script.setAttribute("data-src", dataSrc);
            if (!script.getAttribute("src")) script.setAttribute("src", ftdSrc);
        }

        // Compatibility alias for builds that look up id="myScript".
        let alias = document.getElementById("myScript");
        if (!alias) {
            alias = document.createElement("script");
            alias.id = "myScript";
            alias.type = "text/plain";
            document.head.appendChild(alias);
        }
        alias.setAttribute("security_key", token);
        alias.setAttribute("data-src", dataSrc);
        alias.setAttribute("src", ftdSrc);

        if (typeof window.postData !== "function") {
            throw new Error("FTD loaded but postData() is not available.");
        }
    }

    async _iposGeneratePaymentToken(providerId) {
        const config = await rpc("/payment/ipos_pay/get_config", { provider_id: providerId });
        await this._iposEnsureFtdLoaded(config);

        const tokenData = await new Promise((resolve, reject) => {
            try {
                const ret = window.postData((data) => resolve(data));
                if (ret && typeof ret.then === "function") ret.then(resolve, reject);
            } catch (e) {
                reject(e);
            }
        });

        const token = tokenData?.payment_token_id
            || tokenData?.paymentTokenId
            || tokenData?.payment_token
            || tokenData?.token;
        if (!token) {
            throw new Error("FTD did not return payment token.");
        }
        return token;
    }

    getPaymentAmount() {
        const total = this.getCheckoutGrandTotal();
        const mode = this.state.payment.splitMode;
        if (mode === "full") return total;
        if (mode === "30") return Math.round(total * 0.30 * 100) / 100;
        if (mode === "custom") return Math.round(total * (this.state.payment.customPercent / 100) * 100) / 100;
        return total;
    }

    getTipAmount() {
        const mode = this.state.payment.tipMode;
        const sub = this.getCartTotal();
        if (mode === "none") return 0;
        if (mode === "custom") return this.state.payment.customTip || 0;
        const pct = parseFloat(mode) / 100;
        return Math.round(sub * pct * 100) / 100;
    }

    // ── PLACE ORDER + PAY (cash / check flow) ────────────────────────────────

    async placeOrderAndPay() {
        const method = this.state.payment.method;
        if (!["cash", "check", "credit_card"].includes(method)) {
            alert("Only Cash, Check, and Credit Card payments are currently supported.");
            return;
        }
        if (method === "credit_card") {
            const cardDigits = String(this.state.payment.cardNumber || "").replace(/\D/g, "");
            const expiry = String(this.state.payment.cardExpiry || "");
            const cvv = String(this.state.payment.cardCvv || "");
            const expiryOk = /^(0[1-9]|1[0-2])\/\d{2}$/.test(expiry);
            if (cardDigits.length < 12 || !expiryOk || cvv.length < 3) {
                alert("Please enter valid card number, expiry (MM/YY), and CVV.");
                return;
            }
        }

        if (!this.state.additional.weatherPolicyAgreed || !this.state.additional.setupTermsAgreed) {
            alert("Please agree to both policies before placing the order.");
            return;
        }

        // Cancel any pending auto-save to avoid duplicate partner creation
        if (this._partnerSaveTimer) {
            clearTimeout(this._partnerSaveTimer);
            this._partnerSaveTimer = null;
        }

        try {
            this.state.payment = { ...this.state.payment, processing: true };

            let orderId;
            if (this.state.existingPosOrderId) {
                orderId = this.state.existingPosOrderId;
                await this._syncPartnerAndSaleOrderFromState(orderId);
            } else {
                orderId = await this._createSaleOrder();
            }
            if (!orderId) throw new Error("Order creation returned no ID.");

            const [ordRow] = await this.orm.read("sale.order", [orderId], ["state"]);
            if (ordRow && ["draft", "sent"].includes(ordRow.state)) {
                await this.orm.call("sale.order", "action_confirm", [[orderId]]);
            }

            const splitMode = this.state.payment.splitMode;
            let depositPercent = 0;
            if (splitMode === "30") depositPercent = 30;
            else if (splitMode === "custom") depositPercent = this.state.payment.customPercent;
            else depositPercent = 100;

            const isDownpayment = splitMode !== "full";

            let invoiceId;
            if (isDownpayment) {
                invoiceId = await this.orm.call(
                    "sale.order",
                    "action_create_downpayment_invoice_pos",
                    [[orderId]],
                    { deposit_percent: depositPercent }
                );
                invoiceId = Array.isArray(invoiceId) ? invoiceId[0] : invoiceId;
            } else {
                // Bypass delivered-qty policy issues in POS: create a 100% invoice via the
                // custom downpayment helper, which is designed for this checkout flow.
                invoiceId = await this.orm.call(
                    "sale.order",
                    "action_create_downpayment_invoice_pos",
                    [[orderId]],
                    { deposit_percent: 100 }
                );
                invoiceId = Array.isArray(invoiceId) ? invoiceId[0] : invoiceId;
            }

            // ── Tip line ─────────────────────────────────────────────────────
            const tipAmount = this.getTipAmount();
            if (tipAmount > 0) {
                let tipProductId = false;
                const tipProducts = await this.orm.searchRead(
                    "product.product",
                    [["name", "ilike", "Tip"], ["type", "=", "service"]],
                    ["id"], { limit: 1 }
                );
                if (tipProducts.length) {
                    tipProductId = tipProducts[0].id;
                } else {
                    const tmplId = await this.orm.create("product.template", [{
                        name: "Tip", type: "service", list_price: 0, invoice_policy: "order",
                    }]);
                    const variants = await this.orm.searchRead(
                        "product.product",
                        [["product_tmpl_id", "=", Array.isArray(tmplId) ? tmplId[0] : tmplId]],
                        ["id"], { limit: 1 }
                    );
                    tipProductId = variants[0]?.id || false;
                }

                if (tipProductId && invoiceId) {
                    await this.orm.call("account.move", "write", [[invoiceId], {
                        invoice_line_ids: [[0, 0, {
                            product_id: tipProductId,
                            name: "Tip",
                            quantity: 1,
                            price_unit: tipAmount,
                            is_tip: true,
                            tax_ids: [],
                        }]],
                    }]);
                }
            }

            await this.orm.call("account.move", "action_post", [[invoiceId]]);

            const payAmount = this.getPaymentAmount() + tipAmount;

            const invoiceData = await this.orm.read(
                "account.move", [invoiceId],
                ["amount_residual", "currency_id", "partner_id"]
            );
            const inv = invoiceData[0];
            if (method === "credit_card") {
                const [orderCompany] = await this.orm.read(
                    "sale.order",
                    [orderId],
                    ["company_id"]
                );
                const companyId = orderCompany?.company_id?.[0];
                if (!companyId) {
                    throw new Error("Unable to determine sale order company for payment.");
                }

                const providers = await this.orm.searchRead(
                    "payment.provider",
                    [
                        ["code", "=", "ipos_pay"],
                        ["state", "!=", "disabled"],
                        "|",
                        ["company_id", "=", companyId],
                        ["company_id", "=", false],
                    ],
                    ["id", "name", "payment_method_ids", "company_id"],
                    { limit: 1, context: { allowed_company_ids: [companyId], force_company: companyId } }
                );
                if (!providers.length) {
                    throw new Error("IPOS payment provider not found/enabled.");
                }
                const provider = providers[0];

                const cardMethod = await this.orm.searchRead(
                    "payment.method",
                    [["code", "=", "card"]],
                    ["id"],
                    { limit: 1 }
                );
                if (!cardMethod.length) {
                    throw new Error("Payment method 'card' not found.");
                }

                const txVals = {
                    amount: payAmount,
                    currency_id: inv.currency_id[0],
                    partner_id: inv.partner_id[0],
                    provider_id: provider.id,
                    payment_method_id: cardMethod[0].id,
                    operation: "online_direct",
                    sale_order_ids: [[6, 0, [orderId]]],
                    invoice_ids: [[6, 0, [invoiceId]]],
                    landing_route: "/shop/payment/validate",
                };
                const txId = await this.orm.create(
                    "payment.transaction",
                    [txVals],
                    { context: { allowed_company_ids: [companyId], force_company: companyId } }
                );
                const transactionId = Array.isArray(txId) ? txId[0] : txId;
                const [tx] = await this.orm.read(
                    "payment.transaction",
                    [transactionId],
                    ["reference"],
                    { context: { allowed_company_ids: [companyId], force_company: companyId } }
                );
                if (!tx?.reference) {
                    throw new Error("Failed to create payment transaction reference.");
                }

                const paymentTokenId = await this._iposGeneratePaymentToken(provider.id);
                const charge = await rpc("/payment/ipos_pay/charge_token", {
                    reference: tx.reference,
                    payment_token_id: paymentTokenId,
                });
                if (!charge || charge.state !== "done") {
                    throw new Error(charge?.message || "IPOS charge failed.");
                }

                // Ensure an accounting customer payment exists (account.payment) after gateway success.
                // Odoo should create it during post-processing, but if provider/journal setup is incomplete,
                // force it here so invoices show paid.
                const [txAfter] = await this.orm.read(
                    "payment.transaction",
                    [transactionId],
                    ["payment_id", "state", "is_post_processed"],
                    { context: { allowed_company_ids: [companyId], force_company: companyId } }
                );
                if (!txAfter?.payment_id?.[0]) {
                    try {
                        await this.orm.call(
                            "payment.transaction",
                            "_post_process",
                            [[transactionId]],
                            { context: { allowed_company_ids: [companyId], force_company: companyId } }
                        );
                    } catch (_) {
                        // ignore and try creating payment directly
                    }
                    const [txAfter2] = await this.orm.read(
                        "payment.transaction",
                        [transactionId],
                        ["payment_id"],
                        { context: { allowed_company_ids: [companyId], force_company: companyId } }
                    );
                    if (!txAfter2?.payment_id?.[0]) {
                        await this.orm.call(
                            "payment.transaction",
                            "_create_payment",
                            [[transactionId]],
                            { context: { allowed_company_ids: [companyId], force_company: companyId } }
                        );
                    }
                }
            } else {
                const journals = await this.orm.searchRead(
                    "account.journal",
                    [["type", "=", method === "cash" ? "cash" : "bank"]],
                    ["id", "name"], { limit: 1 }
                );

                if (!journals.length) {
                    throw new Error(
                        `No ${method === "cash" ? "Cash" : "Bank"} journal found. ` +
                        `Please configure one in Odoo ▸ Accounting ▸ Journals.`
                    );
                }

                const journalId = journals[0].id;
                const [journalData] = await this.orm.read(
                    "account.journal",
                    [journalId],
                    ["inbound_payment_method_line_ids"]
                );
                const methodLineIds = journalData?.inbound_payment_method_line_ids || [];
                if (!methodLineIds.length) {
                    throw new Error("No inbound payment method line found on selected journal.");
                }
                const methodLines = await this.orm.searchRead(
                    "account.payment.method.line",
                    [["id", "in", methodLineIds]],
                    ["id", "code"],
                    { order: "id asc" }
                );
                const chosenMethodLine = methodLines.find((l) => l.code === "manual") || methodLines[0];
                const paymentVals = {
                    payment_type: "inbound",
                    partner_type: "customer",
                    partner_id: inv.partner_id[0],
                    amount: payAmount,
                    journal_id: journalId,
                    payment_method_line_id: chosenMethodLine.id,
                    currency_id: inv.currency_id[0],
                    memo: method === "check" && this.state.payment.checkNumber
                        ? `Check #${this.state.payment.checkNumber}`
                        : method === "cash" ? "Cash Payment — POS" : "POS Payment",
                };
                const paymentId = await this.orm.create("account.payment", [paymentVals]);
                const pId = Array.isArray(paymentId) ? paymentId[0] : paymentId;

                await this.orm.call("account.payment", "action_post", [[pId]]);

                const payMoveLines = await this.orm.searchRead(
                    "account.move.line",
                    [
                        ["payment_id", "=", pId],
                        ["account_type", "in", ["asset_receivable", "liability_payable"]],
                    ],
                    ["id"], { limit: 1 }
                );

                if (!payMoveLines.length) {
                    console.warn("[RentalPOS] Could not find payment receivable line for reconciliation.");
                } else {
                    await this.orm.call(
                        "account.move",
                        "js_assign_outstanding_line",
                        [[invoiceId], payMoveLines[0].id]
                    );
                }
            }

            this.state.lastDepositPercent = depositPercent;
            this.state.lastCustomerEmail = this.state.billing.email || "";
            this.state.lastCustomerPartnerId = this.state.billing.selectedPartnerId || false;
            this.state.invoiceId = invoiceId;
            this.state.invoiceSent = false;

            // Full payment: auto-send confirmation email
            if (depositPercent >= 100) {
                try {
                    await this.orm.call(
                        "sale.order",
                        "action_send_payment_confirmation_pos",
                        [[orderId]],
                        { invoice_id: invoiceId }
                    );
                } catch (emailErr) {
                    console.warn("[RentalPOS] Confirmation email failed (non-critical):", emailErr);
                }
            }

            this._resetAfterOrder();
            this.state.createdOrderId = orderId;
            this.state.paidOnSpot = true;
            this.state.page = "success";

        } catch (e) {
            console.error("[RentalPOS] placeOrderAndPay failed", e);
            alert(`Payment failed: ${e.message || e}`);
            if (this.state.existingPosOrderId) {
                await this.refreshExistingOrderPaymentBanner();
            }
        } finally {
            this.state.payment = { ...this.state.payment, processing: false };
        }
    }

    /**
     * Push billing / event / amounts from POS state onto an existing sale.order before payment.
     * Does not replace order lines (those stay as in the database).
     */
    async _syncPartnerAndSaleOrderFromState(orderId) {
        const fullName = `${this.state.billing.firstName} ${this.state.billing.lastName}`.trim();
        let partnerId = this.state.billing.selectedPartnerId;

        if (partnerId) {
            const pv = {
                street: this.state.billing.address || false,
                city: this.state.billing.city || false,
                zip: this.state.billing.zip || false,
                email: this.state.billing.email || false,
                phone: this.state.billing.phone || false,
                phone_secondary: this.state.billing.secondaryPhone || false,
                company_name: this.state.billing.company || false,
            };
            if (this.state.billing.latitude !== null) pv.partner_latitude = this.state.billing.latitude;
            if (this.state.billing.longitude !== null) pv.partner_longitude = this.state.billing.longitude;
            await this.orm.write("res.partner", [partnerId], pv);
        } else if (fullName) {
            const cv = {
                name: fullName,
                email: this.state.billing.email || false,
                phone: this.state.billing.phone || false,
                phone_secondary: this.state.billing.secondaryPhone || false,
                street: this.state.billing.address || false,
                zip: this.state.billing.zip || false,
                city: this.state.billing.city || false,
                company_name: this.state.billing.company || false,
            };
            if (this.state.billing.latitude !== null) cv.partner_latitude = this.state.billing.latitude;
            if (this.state.billing.longitude !== null) cv.partner_longitude = this.state.billing.longitude;
            const cp = await this.orm.create("res.partner", [cv]);
            partnerId = Array.isArray(cp) ? cp[0] : cp;
            this.state.billing.selectedPartnerId = partnerId;
        }

        const soVals = {
            ...(partnerId && { partner_id: partnerId }),
            event_location_name: this.state.event.locationName || false,
            event_same_as_billing: this.state.event.sameAsBilling,
            event_street: this.state.event.address || false,
            event_city: this.state.event.city || false,
            event_zip: this.state.event.zip || false,
            event_type: this.state.event.eventType || false,
            damage_waiver: this.state.event.damageWaiver || "yes",
            event_location: this.state.event.eventLocation || false,
            ...(this.state.event.latitude !== null && { event_latitude: this.state.event.latitude }),
            ...(this.state.event.longitude !== null && { event_longitude: this.state.event.longitude }),
            additional_weather_policy_agreed: this.state.additional.weatherPolicyAgreed,
            additional_setup_terms_agreed: this.state.additional.setupTermsAgreed,
            setup_surface: this.state.additional.setupSurface || false,
            general_discount: this.state.additional.generalDiscount || 0,
            internal_notes: this.state.additional.internalNotes || false,
            note: this.state.additional.customerNotes || false,
            override_travel_fee: this.state.additional.overrideTravelFee || 0,
            override_tax_amount: this.state.additional.overrideTaxAmount || 0,
            miscellaneous_fees: this.state.additional.miscellaneousFees || 0,
            override_deposit_amount: this.getDepositAmount(),
            tip: this.getTipAmount(),
        };
        if (this.state.billing.referral) {
            soVals.how_did_you_hear = this.state.billing.referral;
        }
        await this.orm.write("sale.order", [orderId], soVals);
    }

    // ── _createSaleOrder (shared by both order flows) ─────────────────────────

    async _createSaleOrder() {
        const fullName = `${this.state.billing.firstName} ${this.state.billing.lastName}`.trim();
        let partnerId = false;

        if (this.state.billing.selectedPartnerId) {
            partnerId = this.state.billing.selectedPartnerId;
            const pv = {
                street: this.state.billing.address || false,
                city: this.state.billing.city || false,
                zip: this.state.billing.zip || false,
                email: this.state.billing.email || false,
                phone: this.state.billing.phone || false,
                phone_secondary: this.state.billing.secondaryPhone || false,
                company_name: this.state.billing.company || false,
            };
            if (this.state.billing.latitude !== null) pv.partner_latitude = this.state.billing.latitude;
            if (this.state.billing.longitude !== null) pv.partner_longitude = this.state.billing.longitude;
            await this.orm.write("res.partner", [partnerId], pv);
        } else if (fullName) {
            const cv = {
                name: fullName,
                email: this.state.billing.email || false,
                phone: this.state.billing.phone || false,
                phone_secondary: this.state.billing.secondaryPhone || false,
                street: this.state.billing.address || false,
                zip: this.state.billing.zip || false,
                city: this.state.billing.city || false,
                company_name: this.state.billing.company || false,
            };
            if (this.state.billing.latitude !== null) cv.partner_latitude = this.state.billing.latitude;
            if (this.state.billing.longitude !== null) cv.partner_longitude = this.state.billing.longitude;
            const cp = await this.orm.create("res.partner", [cv]);
            partnerId = Array.isArray(cp) ? cp[0] : cp;
        }

        const toOdooUTC = (dateStr, timeStr) => {
            if (!dateStr || !timeStr) return false;
            const d = new Date(`${dateStr}T${timeStr}:00`);
            const pad = n => String(n).padStart(2, "0");
            return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:00`;
        };

        const saleTaxId = this.state.companySalesTax.id;

        const orderLines = [];
        for (const item of this.state.cart) {
            const variants = await this.orm.searchRead(
                "product.product",
                [["product_tmpl_id", "=", item.productId]],
                ["id"], { limit: 1 }
            );
            if (!variants.length) continue;

            let startDate = false, endDate = false;
            if (item.date && item.startTime) startDate = toOdooUTC(item.date, item.startTime);
            if (item.date && item.endTime) {
                const [sh, sm] = (item.startTime || "00:00").split(":").map(Number);
                const [eh, em] = item.endTime.split(":").map(Number);
                const endDay = (eh < sh || (eh === sh && em < sm)) ? this._addDays(item.date, 1) : item.date;
                endDate = toOdooUTC(endDay, item.endTime);
            }

            orderLines.push([0, 0, {
                product_id: variants[0].id,
                // Respect manual price override; fall back to auto-calculated unit price
                price_unit: item.customPrice !== undefined ? item.customPrice : this.getItemPrice(item),
                product_uom_qty: item.qty || 1,
                is_rental: true,
                ...(saleTaxId && { tax_ids: [[6, 0, [saleTaxId]]] }),
                ...(startDate && { start_date: startDate }),
                ...(endDate && { return_date: endDate }),
            }]);
        }

        const firstItem = this.state.cart.find(i => i.date && i.startTime);
        const orderRentalStart = firstItem ? toOdooUTC(firstItem.date, firstItem.startTime) : false;

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
            ...(this.state.event.latitude !== null && { event_latitude: this.state.event.latitude }),
            ...(this.state.event.longitude !== null && { event_longitude: this.state.event.longitude }),
            additional_weather_policy_agreed: this.state.additional.weatherPolicyAgreed,
            additional_setup_terms_agreed: this.state.additional.setupTermsAgreed,
            setup_surface: this.state.additional.setupSurface || false,
            general_discount: this.state.additional.generalDiscount || 0,
            internal_notes: this.state.additional.internalNotes || false,
            note: this.state.additional.customerNotes || false,
            override_travel_fee: this.state.additional.overrideTravelFee || 0,
            override_tax_amount: this.state.additional.overrideTaxAmount || 0,
            miscellaneous_fees: this.state.additional.miscellaneousFees || 0,
            override_deposit_amount: this.getDepositAmount(),
            tip: this.getTipAmount(),
            order_line: orderLines,
        };

        const co = await this.orm.create("sale.order", [orderVals], {
            context: { in_rental_app: 1, default_is_rental_order: 1 },
        });
        return Array.isArray(co) ? co[0] : co;
    }

    // ── RESET ─────────────────────────────────────────────────────────────────

    /** Clear persisted POS data and land on the category step (e.g. Book Now from calendar). */
    _prepareFreshCategoriesSession() {
        try {
            localStorage.removeItem("rental_pos_state");
        } catch (_) {
            /* ignore */
        }
        this._resetAfterOrder();
        this.state.page = "categories";
        this.state.products = [];
        this.state.selectedCategoryId = null;
        this.state.selectedCategoryName = "";
        this.state.expandedCard = null;
        this.state.addonProducts = [];
        this.state.createdOrderId = null;
        this.state.paidOnSpot = false;
        this.state.loading = false;
    }

    _resetAfterOrder() {
        this.state.cart = [];
        this.state.pricingSelections = {};
        this.state.billing = {
            selectedPartnerId: false, firstName: "", lastName: "", company: "",
            email: "", phone: "", secondaryPhone: "", address: "", zip: "",
            city: "", state: "", referral: "", latitude: null, longitude: null,
        };
        this.state.event = {
            locationName: "", sameAsBilling: false, address: "", city: "", state: "",
            zip: "", zipStatus: null, zipRecord: null, eventType: "",
            damageWaiver: "yes", eventLocation: "", latitude: null, longitude: null, stillDeliver: false,
        };
        this.state.additional = {
            weatherPolicyAgreed: false, setupTermsAgreed: false, setupSurface: "",
            generalDiscount: 0, discountApplied: false, discountType: "percent",
            discountDescription: "", miscDescription: "",
            couponCode: "", couponApplied: false,
            couponDiscount: 0, couponError: "", couponLabel: "", internalNotes: "", customerNotes: "",
            overrideTravelFee: 0, depositPercent: 0, overrideTaxAmount: null, miscellaneousFees: 0,
        };
        this.state.payment = {
            enabled: false, method: "cash", checkNumber: "", splitMode: "full",
            customPercent: 100, tipMode: "none", customTip: 0, processing: false,
            cardNumber: "", cardExpiry: "", cardCvv: "",
        };
        this.state.billingAddressRaw = "";
        this.state.eventAddressRaw = "";
        this.state.travelFeeInfo = null;
        this.state.showEditDate = false;
        this.state.existingPosOrderId = null;
        this.state.existingOrderPaymentBanner = null;
        localStorage.removeItem("rental_pos_state");
    }
    async loadUserGroup() {
        try {
            this.state.isFreedomFunAdmin = await user.hasGroup("custom_rental.group_freedom_fun_admin");
        } catch (e) {
            console.error("[RentalPOS] loadUserGroup failed", e);
            this.state.isFreedomFunAdmin = false;
        }
    }
}

RentalPosPage.template = "custom_rental.RentalPosView";
registry.category("actions").add("rental_pos_page", RentalPosPage);

patch(ControlPanel.prototype, {
    setup() {
        super.setup();
        this._actionService = useService("action");
        this.__rentalPosVisible = false;
        onMounted(() => { this.__rentalPosVisible = window.location.pathname.includes("/odoo/rental"); this.render(true); });
        onPatched(() => { const r = window.location.pathname.includes("/odoo/rental"); if (this.__rentalPosVisible !== r) { this.__rentalPosVisible = r; this.render(true); } });
    },
    get rentalPosVisible() { return this.__rentalPosVisible || false; },
    openRentalPos() {
        try {
            localStorage.removeItem("rental_pos_state");
        } catch (_) {
            /* ignore */
        }
        this._actionService.doAction({
            type: "ir.actions.client",
            tag: "rental_pos_page",
            name: "Rental POS",
            context: { rental_pos_fresh_categories: true },
        });
    },
});