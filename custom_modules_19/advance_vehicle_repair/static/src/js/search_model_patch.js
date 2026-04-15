import { patch } from '@web/core/utils/patch';
import { AccountProductCatalogSearchPanel } from '@account/components/product_catalog/search/search_panel';

patch(AccountProductCatalogSearchPanel.prototype, {

    setup() {
        super.setup(...arguments);
        this._vehicleDomain = [];
    },

    /**
     * Called by panel_patch.js → _applyVehicleFilter().
     * Injects the vehicle domain into the search model and triggers reload.
     */
    _applyVehicleCompatibilityDomain(domain) {
        this._vehicleDomain = domain || [];
        const searchModel = this.env.searchModel;

        if (!searchModel) return;

        // One-time: shadow the `domain` getter on this specific instance
        if (!searchModel.__vehiclePanelPatched) {
            // Find the `domain` getter by walking the prototype chain
            let domainGetter = null;
            let proto = Object.getPrototypeOf(searchModel);
            while (proto && proto !== Object.prototype) {
                const desc = Object.getOwnPropertyDescriptor(proto, 'domain');
                if (desc && desc.get) {
                    domainGetter = desc.get;
                    break;
                }
                proto = Object.getPrototypeOf(proto);
            }

            if (domainGetter) {
                // Shadow getter on the instance
                Object.defineProperty(searchModel, 'domain', {
                    get() {
                        const base = domainGetter.call(this);
                        const extra = this.__vehicleDomain || [];
                        return extra.length > 0 ? [...base, ...extra] : base;
                    },
                    configurable: true,
                    enumerable: false,
                });
            } else {
                // Fallback: domain is a plain property — capture current value
                const originalDomain = searchModel.domain || [];
                Object.defineProperty(searchModel, 'domain', {
                    get() {
                        const extra = this.__vehicleDomain || [];
                        return extra.length > 0 ? [...originalDomain, ...extra] : originalDomain;
                    },
                    configurable: true,
                    enumerable: false,
                });
            }

            searchModel.__vehiclePanelPatched = true;
        }

        // Update the vehicle domain on the searchModel instance
        searchModel.__vehicleDomain = this._vehicleDomain;

        // Trigger re-search
        searchModel.search();
    },
});
