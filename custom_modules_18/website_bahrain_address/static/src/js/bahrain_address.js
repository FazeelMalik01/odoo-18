import publicWidget from "@web/legacy/js/public/public_widget";
import "@website_sale/js/address";

publicWidget.registry.websiteSaleAddress.include({

    start() {
        this._moveCountryUp();
        return this._super(...arguments);
    },

    async _changeCountry(init = false) {
        await this._super(init);
        this._applyBahrainMode();
    },

    _isBahrainSelected() {
        const select = this.addressForm.country_id;
        if (!select) return false;
        const opt = select.options[select.selectedIndex];
        return opt ? opt.getAttribute("code") === "BH" : false;
    },

    _moveCountryUp() {
        const divStreet  = document.getElementById("div_street");
        const divCountry = document.getElementById("div_country");
        const divState   = document.getElementById("div_state");
        if (!divStreet || !divCountry) return;

        const row = divStreet.parentNode;
        const wBreak = document.createElement("div");
        wBreak.className = "w-100";

        row.insertBefore(divCountry, divStreet);
        if (divState) row.insertBefore(divState, divStreet);
        row.insertBefore(wBreak, divStreet);
    },

    // Only street, street2 and state are hidden for Bahrain.
    // Mobile (div_mobile) is always visible regardless of country.
    _HIDDEN_FOR_BAHRAIN: ["div_street", "div_street2", "div_state"],

    _applyBahrainMode() {
        const isBahrain = this._isBahrainSelected();

        // ── Hide / restore standard fields not relevant to Bahrain ────────────
        this._HIDDEN_FOR_BAHRAIN.forEach((id) => {
            const el = document.getElementById(id);
            if (!el) return;

            if (isBahrain) {
                el.style.display = "none";
                el.querySelectorAll("input, select").forEach((inp) => {
                    // Cache required state so we can restore it on country change
                    if (inp.hasAttribute("required")) {
                        inp.dataset.bahrainWasRequired = "1";
                    }
                    inp.removeAttribute("required");
                    inp.value = "";
                });
            } else {
                el.style.display = "";
                el.querySelectorAll("input, select").forEach((inp) => {
                    if (inp.dataset.bahrainWasRequired === "1") {
                        inp.setAttribute("required", "required");
                        delete inp.dataset.bahrainWasRequired;
                    }
                });
            }
        });

        // ── Bahrain custom fields container ───────────────────────────────────
        const bahrainDiv = document.getElementById("div_bahrain_fields");
        if (bahrainDiv) {
            bahrainDiv.style.display = isBahrain ? "block" : "none";
        }

        // ── required on Bahrain mandatory inputs ──────────────────────────────
        document.querySelectorAll(".bahrain-required").forEach((inp) => {
            if (isBahrain) {
                inp.setAttribute("required", "required");
            } else {
                inp.removeAttribute("required");
                inp.value = "";
            }
        });

        // ── Clear Bahrain-only optional field when switching away ─────────────
        if (!isBahrain) {
            const flatInp = document.getElementById("bahrain_flat");
            if (flatInp) flatInp.value = "";
        }
    },
});