console.log('address mapbox loaded');

import { patch }         from "@web/core/utils/patch";
import { CharField }     from "@web/views/fields/char/char_field";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { useService }    from "@web/core/utils/hooks";

const MAPBOX_TOKEN = your_token_here;

const STREET_FIELD_NAMES = new Set(["street", "partner_street_display", "event_street"]);

// ── Helpers ───────────────────────────────────────────────────────────────────

function newToken() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
        const r = (Math.random() * 16) | 0;
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
}

async function mbSuggest(query, sessionToken) {
    if (!query || query.length < 3) return [];
    try {
        const p = new URLSearchParams({
            q:             query,
            access_token:  MAPBOX_TOKEN,
            session_token: sessionToken,
            country:       "us",
            limit:         "5",
            types:         "address,street,place",
        });
        const r = await fetch(`https://api.mapbox.com/search/searchbox/v1/suggest?${p}`);
        if (!r.ok) return [];
        return (await r.json()).suggestions || [];
    } catch (e) {
        console.error("[MapboxPartner] suggest error", e);
        return [];
    }
}

async function mbRetrieve(mapboxId, sessionToken) {
    try {
        const p = new URLSearchParams({
            access_token:  MAPBOX_TOKEN,
            session_token: sessionToken,
        });
        const r = await fetch(
            `https://api.mapbox.com/search/searchbox/v1/retrieve/${encodeURIComponent(mapboxId)}?${p}`
        );
        if (!r.ok) return null;
        return (await r.json()).features?.[0]?.properties || null;
    } catch (e) {
        console.error("[MapboxPartner] retrieve error", e);
        return null;
    }
}

function parseFeature(props) {
    const ctx    = props.context     || {};
    const coords = props.coordinates || {};
    return {
        street:      props.address             || ctx.street?.name || "",
        city:        ctx.place?.name           || "",
        state:       ctx.region?.name          || "",
        zip:         ctx.postcode?.name        || "",
        country:     ctx.country?.name         || "",
        countryCode: ctx.country?.country_code || "",
        latitude:    coords.latitude            ?? null,
        longitude:   coords.longitude           ?? null,
    };
}

function debounce(fn, ms) {
    let t;
    return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

function escHtml(s) {
    return String(s || "")
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function resolveCoordTarget(fieldName, record) {
    if (fieldName === "partner_street_display") {
        // sale.order — write to the linked partner
        const partnerId =
            record.data?.partner_id?.[0] ??
            record.data?.partner_id?.id  ??
            null;
        if (!partnerId) {
            console.warn("[MapboxPartner] partner_id not found on sale.order record");
            return null;
        }
        return { model: "res.partner", resId: partnerId };
    }

    if (fieldName === "event_street") {
        return null;
    }

    // Default: write directly on the current record (res.partner / res.company)
    const resId =
        record.resId            ??
        record.data?.id         ??
        record.id               ?? null;

    const model =
        record.resModel          ??
        record.model?.resModel   ??
        record.model?.modelName  ??
        "res.partner";

    if (!resId) return null;
    return { model, resId };
}

function resolveAddressFieldNames(streetFieldName) {
    if (streetFieldName === "partner_street_display") {
        return { cityField: "partner_city_display", zipField: "partner_zip_display" };
    }
    if (streetFieldName === "event_street") {
        return { cityField: "event_city", zipField: "event_zip" };
    }
    return { cityField: "city", zipField: "zip" };
}

// ── Patch CharField ───────────────────────────────────────────────────────────

patch(CharField.prototype, {
    setup() {
        super.setup();

        // Only activate for recognised street field names
        if (!STREET_FIELD_NAMES.has(this.props?.name)) return;

        this._mbFieldName = this.props.name;
        this._mbOrm       = useService("orm");

        this._mb = {
            token:            newToken(),
            suggestions:      [],
            show:             false,
            dd:               null,
            input:            null,
            pendingLatitude:  null,
            pendingLongitude: null,
            pendingStateId:   null,
            pendingCountryId: null,
            _origSave:        null,
            _savePatched:     false,
        };

        this._mbSuggest = debounce(async (q) => {
            const list = await mbSuggest(q, this._mb.token);
            this._mb.suggestions = list;
            this._mb.show        = list.length > 0;
            this._mbRender();
        }, 300);

        onMounted(()     => this._mbMount());
        onWillUnmount(() => this._mbDestroy());
    },

    _mbMount() {
        if (!this._mb) return;
        let input = this._mbFindInput();
        if (!input) {
            console.warn("[MapboxPartner] <input> not found, retrying in 200 ms…");
            setTimeout(() => {
                input = this._mbFindInput();
                if (input) this._mbAttach(input);
                else console.error("[MapboxPartner] <input> still not found — giving up.");
            }, 200);
            return;
        }
        this._mbAttach(input);
    },

    _mbFindInput() {
        const fiber = this.__owl__;
        if (!fiber) return null;
        const el = this._mbExtractEl(fiber.bdom);
        if (el && el.nodeType === 1) {
            const input = el.tagName === "INPUT" ? el : el.querySelector("input");
            if (input) return input;
        }
        const selector = `.o_field_widget[name='${this._mbFieldName}'] input`;
        const widgets  = document.querySelectorAll(selector);
        if (widgets.length === 1) return widgets[0];
        if (widgets.length > 1) {
            const active = document.querySelector(
                `.o_form_view.o_form_editable .o_field_widget[name='${this._mbFieldName}'] input`
            );
            return active || widgets[0];
        }
        return null;
    },

    _mbExtractEl(bdom) {
        if (!bdom) return null;
        if (bdom.el && bdom.el.nodeType === 1) return bdom.el;
        if (bdom.el && bdom.el.nodeType === 3) return bdom.el.parentElement;
        if (Array.isArray(bdom.children)) {
            for (const c of bdom.children) {
                const found = this._mbExtractEl(c);
                if (found) return found;
            }
        }
        if (bdom.child) return this._mbExtractEl(bdom.child);
        if (bdom.component?.__owl__) return this._mbExtractEl(bdom.component.__owl__.bdom);
        return null;
    },

    _mbAttach(input) {
        if (!this._mb) return;
        console.log(`[MapboxPartner] attached to input (field: ${this._mbFieldName}):`, input);
        this._mb.input = input;

        const wrapper = input.closest(".o_field_widget") || input.parentElement;
        if (wrapper) wrapper.style.position = "relative";

        const dd = document.createElement("div");
        dd.style.cssText = [
            "position:absolute", "top:100%", "left:0", "right:0",
            "z-index:9999", "background:#fff",
            "border:1px solid #dee2e6", "border-radius:4px",
            "box-shadow:0 4px 12px rgba(0,0,0,.15)",
            "max-height:220px", "overflow-y:auto", "display:none",
        ].join(";");
        wrapper.appendChild(dd);
        this._mb.dd = dd;

        this._mbOnInput = (e) => {
            const val = e.target.value;
            if (val.length < 3) {
                this._mb.show = false;
                this._mb.suggestions = [];
                this._mbRender();
                return;
            }
            this._mbSuggest(val);
        };
        this._mbOnBlur = () => setTimeout(() => {
            this._mb.show = false;
            this._mbRender();
        }, 200);

        input.addEventListener("input", this._mbOnInput);
        input.addEventListener("blur",  this._mbOnBlur);

        const record = this.props?.record;
        if (record && typeof record.save === "function" && !this._mb._savePatched) {
            this._mb._origSave    = record.save.bind(record);
            this._mb._savePatched = true;

            // Post-save hook: write lat/lon + state_id + country_id directly via ORM.
            // Many2one fields (state_id, country_id) cannot be set via record.update() in OWL
            // because the relational model ignores external [id, name] updates for those fields.
            // Direct ORM write after save is the reliable path.
            record.save = async (...args) => {
                const result = await this._mb._origSave(...args);

                const lat       = this._mb?.pendingLatitude;
                const lon       = this._mb?.pendingLongitude;
                const stateId   = this._mb?.pendingStateId;
                const countryId = this._mb?.pendingCountryId;

                const hasCoords  = lat !== null && lon !== null;
                const hasRelated = !!(stateId || countryId);

                if (hasCoords || hasRelated) {
                    const target = resolveCoordTarget(this._mbFieldName, record);

                    if (target) {
                        try {
                            const vals = {};
                            if (hasCoords) {
                                vals.partner_latitude  = lat;
                                vals.partner_longitude = lon;
                            }
                            // Set country_id before state_id so the FK constraint is satisfied
                            if (countryId) vals.country_id = countryId;
                            if (stateId)   vals.state_id   = stateId;

                            console.log(
                                `[MapboxPartner] post-save write → ${target.model} [${target.resId}]`,
                                vals
                            );
                            await this._mbOrm.write(target.model, [target.resId], vals);
                            console.log("[MapboxPartner] post-save write ✓");

                            if (typeof record.load === "function") {
                                await record.load();
                                console.log("[MapboxPartner] record reloaded ✓");
                            }
                        } catch (e) {
                            console.error("[MapboxPartner] post-save write failed:", e);
                        }
                    }

                    if (this._mb) {
                        this._mb.pendingLatitude  = null;
                        this._mb.pendingLongitude = null;
                        this._mb.pendingStateId   = null;
                        this._mb.pendingCountryId = null;
                    }
                }

                return result;
            };
        }
    },

    _mbRender() {
        const { dd, show, suggestions } = this._mb || {};
        if (!dd) return;
        if (!show || !suggestions.length) {
            dd.style.display = "none";
            dd.innerHTML     = "";
            return;
        }
        dd.innerHTML = suggestions.map((s, i) => `
            <div class="mb-item" data-idx="${i}"
                 style="display:flex;align-items:flex-start;gap:8px;
                        padding:8px 12px;cursor:pointer;
                        border-bottom:1px solid #f0f0f0;">
                <i class="fa fa-map-marker"
                   style="color:#6c757d;margin-top:2px;flex-shrink:0;"></i>
                <div>
                    <div style="font-size:13px;font-weight:600;">${escHtml(s.name)}</div>
                    <small style="color:#6c757d;">${escHtml(s.place_formatted || s.full_address || "")}</small>
                </div>
            </div>`).join("");

        dd.querySelectorAll(".mb-item").forEach((el, i) => {
            el.addEventListener("mouseenter", () => el.style.background = "#f8f9fa");
            el.addEventListener("mouseleave", () => el.style.background = "");
            el.addEventListener("mousedown",  (e) => { e.preventDefault(); this._mbSelect(suggestions[i]); });
        });
        dd.style.display = "block";
    },

    async _mbSelect(suggestion) {
        this._mb.show        = false;
        this._mb.suggestions = [];
        this._mbRender();

        const props = await mbRetrieve(suggestion.mapbox_id, this._mb.token);
        this._mb.token = newToken();
        if (!props) return;

        const addr   = parseFeature(props);
        const street = addr.street || suggestion.address || suggestion.name || "";

        console.log(`[MapboxPartner] selected addr (field: ${this._mbFieldName}):`, addr);

        const record = this.props?.record;
        if (!record) return;

        // ── Step 1: patch char fields immediately via record.update() ──────────
        const { cityField, zipField } = resolveAddressFieldNames(this._mbFieldName);
        const charUpdates = { [this._mbFieldName]: street };
        if (addr.city) charUpdates[cityField] = addr.city;
        if (addr.zip)  charUpdates[zipField]  = addr.zip;
        await record.update(charUpdates);

        if (this._mb?.input) this._mb.input.value = street;

        // ── Step 2: queue lat/lon for post-save write ──────────────────────────
        if (addr.latitude !== null && addr.longitude !== null) {
            this._mb.pendingLatitude  = addr.latitude;
            this._mb.pendingLongitude = addr.longitude;
        }

        // ── Step 3: resolve & patch country_id / state_id ─────────────────────
        // Only applies to the res.partner "street" field (not sale.order display fields).
        // Two-pronged approach:
        //   a) record.update() with [id, display_name] format for immediate visual feedback
        //   b) pendingStateId/pendingCountryId queued for guaranteed post-save ORM write
        if (this._mbFieldName === "street") {
            let countryId      = null;
            let countryDispName = "";
            let stateId        = null;
            let stateDispName  = "";

            // Resolve country
            if (addr.countryCode || addr.country) {
                try {
                    const domain = addr.countryCode
                        ? [["code", "=", addr.countryCode.toUpperCase()]]
                        : [["name", "=", addr.country]];
                    const rows = await this._mbOrm.searchRead(
                        "res.country", domain, ["id", "display_name"], { limit: 1 }
                    );
                    if (rows.length) {
                        countryId       = rows[0].id;
                        countryDispName = rows[0].display_name;
                        console.log(`[MapboxPartner] country: "${addr.countryCode}" → id=${countryId} "${countryDispName}"`);
                    } else {
                        console.warn(`[MapboxPartner] country not found: "${addr.countryCode || addr.country}"`);
                    }
                } catch (e) {
                    console.warn("[MapboxPartner] country lookup failed:", e);
                }
            }

            // Resolve state (scoped to the resolved country for accuracy)
            if (addr.state) {
                try {
                    const domain = [["name", "=", addr.state]];
                    if (countryId) domain.push(["country_id", "=", countryId]);
                    const rows = await this._mbOrm.searchRead(
                        "res.country.state", domain, ["id", "display_name"], { limit: 1 }
                    );
                    if (rows.length) {
                        stateId       = rows[0].id;
                        stateDispName = rows[0].display_name;
                        console.log(`[MapboxPartner] state: "${addr.state}" → id=${stateId} "${stateDispName}"`);
                    } else {
                        console.warn(`[MapboxPartner] state not found: "${addr.state}"`);
                    }
                } catch (e) {
                    console.warn("[MapboxPartner] state lookup failed:", e);
                }
            }

            // a) Immediate visual update — set country first, then state
            //    (state_id field context depends on country_id being set)
            try {
                if (countryId) {
                    await record.update({ country_id: [countryId, countryDispName] });
                }
                if (stateId) {
                    await record.update({ state_id: [stateId, stateDispName] });
                }
            } catch (e) {
                console.warn("[MapboxPartner] record.update for Many2one failed (will rely on post-save write):", e);
            }

            // b) Queue for post-save ORM write (guaranteed persistence path)
            if (countryId) this._mb.pendingCountryId = countryId;
            if (stateId)   this._mb.pendingStateId   = stateId;
        }
    },

    _mbDestroy() {
        if (!this._mb) return;
        const record = this.props?.record;
        if (record && this._mb._savePatched && this._mb._origSave) {
            record.save = this._mb._origSave;
        }
        const { input, dd } = this._mb;
        if (input) {
            input.removeEventListener("input", this._mbOnInput);
            input.removeEventListener("blur",  this._mbOnBlur);
        }
        if (dd) dd.remove();
        this._mb = null;
    },
});
