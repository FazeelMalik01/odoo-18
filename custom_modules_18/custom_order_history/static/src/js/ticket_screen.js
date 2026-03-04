/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { fuzzyLookup } from "@web/core/utils/search";
import { parseUTCString } from "@point_of_sale/utils";

const NBR_BY_PAGE = 30;

patch(TicketScreen.prototype, {
    /**
     * Override setup to store partner ID from state override
     */
    setup() {
        super.setup(...arguments);
        // Store partner ID if provided in state override
        if (this.props.stateOverride?.partnerId) {
            this.partnerIdFilter = this.props.stateOverride.partnerId;
            // Reset page when filtering by specific partner
            if (this.state) {
                this.state.page = 1;
            }
        }
    },

    /**
     * Override _computeSyncedOrdersDomain to filter by partner ID when available
     * This ensures orders are filtered by the specific customer ID instead of name
     */
    _computeSyncedOrdersDomain() {
        // If we have a partner ID filter, use it directly
        if (this.partnerIdFilter) {
            return [["partner_id", "=", this.partnerIdFilter]];
        }

        // Otherwise, use the default search logic
        let { fieldName, searchTerm } = this.state.search;
        if (!searchTerm) {
            return [];
        }

        // Note: We don't check for PARTNER_ID field here anymore
        // because we use partnerIdFilter for ID-based filtering
        // and PARTNER field for displaying the name in search bar

        const searchField = this._getSearchFields()[fieldName];
        if (searchField && searchField.modelField && searchField.modelField !== null) {
            if (searchField.formatSearch) {
                searchTerm = searchField.formatSearch(searchTerm);
            }
            return [[searchField.modelField, "ilike", `%${searchTerm}%`]];
        } else {
            return [];
        }
    },

    /**
     * Override getFilteredOrderList to also filter by partner ID for active orders
     * Note: For SYNCED orders, filtering happens in the backend via domain.
     * This filter is mainly for active (non-synced) orders.
     */
    getFilteredOrderList() {
        const orderModel = this.pos.models["pos.order"];
        let orders =
            this.state.filter === "SYNCED"
                ? orderModel.filter((o) => o.finalized && o.uiState.displayed)
                : orderModel.filter(this.activeOrderFilter);

        // Filter by partner ID if we have a specific partner ID filter
        // This is important for active orders that haven't been synced yet
        if (this.partnerIdFilter) {
            orders = orders.filter((order) => {
                return order.partner_id?.id === this.partnerIdFilter;
            });
        }

        if (this.state.filter && !["ACTIVE_ORDERS", "SYNCED"].includes(this.state.filter)) {
            orders = orders.filter((order) => {
                const screen = order.get_screen_data();
                return this._getScreenToStatusMap()[screen.name] === this.state.filter;
            });
        }

        if (this.state.search.searchTerm) {
            // Skip name-based search if we're filtering by partner ID
            // The searchTerm shows the customer name for display, but we filter by ID
            if (this.partnerIdFilter) {
                // Already filtered by partner ID above, skip name-based fuzzy search
            } else {
                const repr = this._getSearchFields()[this.state.search.fieldName]?.repr;
                if (repr) {
                    orders = fuzzyLookup(this.state.search.searchTerm, orders, repr);
                }
            }
        }

        const sortOrders = (orders, ascending = false) =>
            orders.sort((a, b) => {
                const dateA = parseUTCString(a.date_order, "yyyy-MM-dd HH:mm:ss");
                const dateB = parseUTCString(b.date_order, "yyyy-MM-dd HH:mm:ss");

                if (a.date_order !== b.date_order) {
                    return ascending ? dateA - dateB : dateB - dateA;
                } else {
                    const nameA = parseInt(a.name.replace(/\D/g, "")) || 0;
                    const nameB = parseInt(b.name.replace(/\D/g, "")) || 0;
                    return ascending ? nameA - nameB : nameB - nameA;
                }
            });

        if (this.state.filter === "SYNCED") {
            return sortOrders(orders).slice(
                (this.state.page - 1) * NBR_BY_PAGE,
                this.state.page * NBR_BY_PAGE
            );
        } else {
            return sortOrders(orders, true);
        }
    },
});
