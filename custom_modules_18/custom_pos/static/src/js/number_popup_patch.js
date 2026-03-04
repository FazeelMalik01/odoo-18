import { patch } from "@web/core/utils/patch";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";

patch(NumberPopup.prototype, {
    setup() {
        super.setup(...arguments);
        const title = (this.props?.title || "").toLowerCase();
        // Set a flag on the numberBuffer service to skip formatting
        this.numberBuffer.isPinEntry =
            title.includes("password") ||
            title.includes("passcode") ||
            title.includes("pin");
    },

    confirm() {
        if (this.numberBuffer.isPinEntry) {
            // RAW buffer — allow leading zeros
            this.props.getPayload(this.state.buffer);
            this.props.close();
            return;
        }
        // Normal number popup: clean commas
        let payload = this.state.buffer.replace(/,/g, "");
        this.props.getPayload(payload);
        this.props.close();
    },
});
