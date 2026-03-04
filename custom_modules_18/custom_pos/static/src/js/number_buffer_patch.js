/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const numberBufferService = registry.category("services").get("number_buffer");

if (numberBufferService) {
    const originalStart = numberBufferService.start;

    numberBufferService.start = async (env, deps) => {
        const numberBuffer = await originalStart(env, deps);

        patch(numberBuffer, {

            // Helper: check if current popup is a PIN/password popup
            _isPinPopup() {
                // Use flag set by NumberPopup
                if (this.isPinEntry) return true;

                // Safe fallback: try to read popup title
                const popupService = this.env?.services?.popup;
                const current = popupService?.currentPopup;
                const title = current?.props?.title?.toString().toLowerCase() || "";
                return title.includes("password") || title.includes("passcode") || title.includes("pin");
            },

            _updateBuffer(input) {
                const res = super._updateBuffer ? super._updateBuffer(input) : (this._super ? this._super(input) : undefined);

                // Skip formatting for PIN
                if (this._isPinPopup()) return res;

                try {
                    if (!this.state?.buffer) return res;

                    const clean = this.state.buffer.replace(/,/g, "");

                    if (!isNaN(clean) && clean !== "" && !this.state.buffer.endsWith(this.decimalPoint)) {
                        const [intPart, decPart] = clean.split(this.decimalPoint);
                        const formatted = Number(intPart).toLocaleString("en-US") + (decPart ? this.decimalPoint + decPart : "");

                        this.trigger("buffer-update", formatted);
                        this.state._rawBuffer = clean; // store clean value
                    }
                } catch (err) {
                    console.warn("Number formatting failed:", err);
                }

                return res;
            },

            sendKey(key) {
                if (!this._isPinPopup() && this.state?.buffer?.includes(",")) {
                    this.state.buffer = this.state.buffer.replace(/,/g, "");
                }
                return super.sendKey ? super.sendKey(key) : (this._super ? this._super(key) : undefined);
            },

            confirm(value) {
                // Raw value for PIN
                if (this._isPinPopup()) {
                    return super.confirm ? super.confirm(this.state.buffer) : (this._super ? this._super(this.state.buffer) : undefined);
                }

                // Clean commas for normal popups
                try {
                    if (typeof value === "string") value = value.replace(/,/g, "");
                    if ((value === "" || value == null) && this.state?._rawBuffer) {
                        value = this.state._rawBuffer;
                    }
                } catch (e) {}

                return super.confirm ? super.confirm(value) : (this._super ? this._super(value) : undefined);
            },
        });

        return numberBuffer;
    };
}
