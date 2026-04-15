/** @odoo-module **/

import { onWillStart, useState } from '@odoo/owl';
import { rpc } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';
import { AccountProductCatalogSearchPanel } from '@account/components/product_catalog/search/search_panel';

patch(AccountProductCatalogSearchPanel.prototype, {

    setup() {
        super.setup();

        // Extend state with vehicle filter state + part condition filter
        Object.assign(this.state, {
            vehicleMakes: [],
            vehicleModels: [],
            vehicleYears: [],
            selectedMakeId: null,
            selectedModelId: null,
            selectedYearId: null,        // single year dropdown
            vehiclePanelExpanded: true,
            selectedPartCondition: null, // null = all, 'new' | 'used' | 'commercial'
        });

        // Load all three independently on start
        onWillStart(async () => {
            await Promise.all([
                this._loadVehicleMakes(),
                this._loadAllVehicleModels(),
                this._loadAllVehicleYears(),
            ]);
        });
    },

    // ─── Loaders ─────────────────────────────────────────────────────────────

    async _loadVehicleMakes() {
        try {
            this.state.vehicleMakes = await rpc('/web/dataset/call_kw', {
                model: 'vehicle.brand',
                method: 'search_read',
                args: [[]],
                kwargs: { fields: ['id', 'name'], order: 'name asc' },
            });
        } catch (e) {
            console.warn('[VehicleFilter] Could not load makes', e);
        }
    },

    async _loadAllVehicleModels() {
        // Load models filtered by make if one is selected, else all models
        const domain = this.state.selectedMakeId
            ? [['brand_id', '=', this.state.selectedMakeId]]
            : [];
        try {
            this.state.vehicleModels = await rpc('/web/dataset/call_kw', {
                model: 'vehicle.model',
                method: 'search_read',
                args: [domain],
                kwargs: { fields: ['id', 'name', 'brand_id'], order: 'name asc' },
            });
        } catch (e) {
            console.warn('[VehicleFilter] Could not load models', e);
        }
    },

    async _loadAllVehicleYears() {
        // vehicle.model.year may not have a direct model_id field.
        // Load all years always — they are typically just year numbers (2020, 2021 etc.)
        // and the actual filtering happens via vehicle_compatibility_ids domain.
        try {
            const years = await rpc('/web/dataset/call_kw', {
                model: 'vehicle.model.year',
                method: 'search_read',
                args: [[]],
                kwargs: { fields: ['id', 'name'], order: 'name desc' },
            });
            this.state.vehicleYears = years;
        } catch (e) {
            console.warn('[VehicleFilter] Could not load years', e);
            this.state.vehicleYears = [];
        }
    },

    // ─── DOM Event Handlers ──────────────────────────────────────────────────

    async onMakeChange(ev) {
        const makeId = parseInt(ev.target.value) || null;
        this.state.selectedMakeId = makeId;
        this.state.selectedModelId = null;
        this.state.selectedYearId = null;
        await this._loadAllVehicleModels();
        this._applyVehicleFilter();
    },

    async onModelChange(ev) {
        const modelId = parseInt(ev.target.value) || null;
        this.state.selectedModelId = modelId;
        this.state.selectedYearId = null;
        this._applyVehicleFilter();
    },

    onYearChange(ev) {
        this.state.selectedYearId = parseInt(ev.target.value) || null;
        this._applyVehicleFilter();
    },

    /**
     * Handles radio button click for part condition.
     * Clicking the already-selected option deselects it (acts as a toggle/clear).
     */
    onPartConditionChange(ev) {
        const value = ev.target.value;
        // Toggle off if the same option is clicked again
        if (this.state.selectedPartCondition === value) {
            this.state.selectedPartCondition = null;
            // Uncheck the radio visually since radios don't natively deselect
            ev.target.checked = false;
        } else {
            this.state.selectedPartCondition = value;
        }
        this._applyVehicleFilter();
    },

    async clearVehicleFilters() {
        Object.assign(this.state, {
            selectedMakeId: null,
            selectedModelId: null,
            selectedYearId: null,
            selectedPartCondition: null,
        });
        await this._loadAllVehicleModels();
        this._applyVehicleFilter();
    },

    toggleVehiclePanel() {
        this.state.vehiclePanelExpanded = !this.state.vehiclePanelExpanded;
    },

    // ─── Domain Builder ───────────────────────────────────────────────────────

    _applyVehicleFilter() {
        const { selectedMakeId, selectedModelId, selectedYearId, selectedPartCondition } = this.state;
        const compatDomain = [];

        if (selectedMakeId) {
            compatDomain.push(['vehicle_compatibility_ids.make_id', '=', selectedMakeId]);
        }
        if (selectedModelId) {
            compatDomain.push(['vehicle_compatibility_ids.model_id', '=', selectedModelId]);
        }
        if (selectedYearId) {
            compatDomain.push(['vehicle_compatibility_ids.model_year_ids', 'in', [selectedYearId]]);
        }

        // Only show spare parts when any vehicle filter is active
        if (compatDomain.length > 0) {
            compatDomain.push(['spare_part', '=', true]);
        }

        // Part condition filter — works independently of vehicle filters
        if (selectedPartCondition) {
            compatDomain.push(['part_condition', '=', selectedPartCondition]);
        }

        this._applyVehicleCompatibilityDomain(compatDomain);
    },

    // ─── Computed Getters ─────────────────────────────────────────────────────

    get hasVehicleFilters() {
        return !!(
            this.state.selectedMakeId ||
            this.state.selectedModelId ||
            this.state.selectedYearId ||
            this.state.selectedPartCondition
        );
    },

    get selectedMakeName() {
        const m = this.state.vehicleMakes.find(m => m.id === this.state.selectedMakeId);
        return m ? m.name : '';
    },

    get selectedModelName() {
        const m = this.state.vehicleModels.find(m => m.id === this.state.selectedModelId);
        return m ? m.name : '';
    },

    get selectedYearName() {
        const y = this.state.vehicleYears.find(y => y.id === this.state.selectedYearId);
        return y ? y.name : '';
    },

    /**
     * Returns the display label for the currently selected part condition.
     */
    get selectedPartConditionName() {
        const labels = { new: 'New', used: 'Used', commercial: 'Commercial' };
        return this.state.selectedPartCondition
            ? labels[this.state.selectedPartCondition]
            : '';
    },

    /**
     * Static list of part condition options for the template.
     */
    get partConditionOptions() {
        return [
            { value: 'new',        label: 'New'        },
            { value: 'used',       label: 'Used'       },
            { value: 'commercial', label: 'Commercial' },
        ];
    },
});