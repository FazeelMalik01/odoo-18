import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import { onMounted, onPatched } from "@odoo/owl";

patch(FormController.prototype, {

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this._lastPartnerId = null;

        onMounted(() => {
            if (this.model.root.resModel !== "authorize.manual.payment") return;
            const partnerId = this.model.root.data?.partner_id?.[0];
            if (partnerId) {
                this._lastPartnerId = partnerId;
                this._populateCardFields(partnerId);
            }
        });

        onPatched(() => {
            if (this.model.root.resModel !== "authorize.manual.payment") return;
            const partnerId = this.model.root.data?.partner_id?.[0];
            if (partnerId !== this._lastPartnerId) {
                this._lastPartnerId = partnerId;
                if (partnerId) {
                    this._populateCardFields(partnerId);
                } else {
                    this._clearCardFields();
                }
            }
        });
    },

    async beforeExecuteActionButton(clickParams) {
        if (this.model.root.resModel !== "authorize.manual.payment") {
            return super.beforeExecuteActionButton(clickParams);
        }
        if (clickParams.name === "action_process_payment") {
            try {
                await this._tokenizeCard();
            } catch (e) {
                return false;
            }
            await this.model.root.save({ stayInEdition: true });
        }
        return super.beforeExecuteActionButton(clickParams);
    },

    async _populateCardFields(partnerId) {
        try {
            const [partner] = await this.orm.read(
                "res.partner",
                [partnerId],
                ["cc_number", "cc_exp_month", "cc_exp_year", "cc_cvv"]
            );
            const setValue = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val || "";
            };
            setValue("cc_number", partner.cc_number);
            setValue("cc_exp_month", partner.cc_exp_month);
            setValue("cc_exp_year", partner.cc_exp_year);
            setValue("cc_cvv", partner.cc_cvv);
        } catch (e) {
            console.error("Failed to load partner card data:", e);
        }
    },

    _clearCardFields() {
        ["cc_number", "cc_exp_month", "cc_exp_year", "cc_cvv"].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = "";
        });
    },

    async _tokenizeCard() {
        const ccNum = document.getElementById("cc_number")?.value.replace(/\s/g, "");
        const ccMonth = document.getElementById("cc_exp_month")?.value.trim();
        const ccYear = document.getElementById("cc_exp_year")?.value.trim();
        const ccCvv = document.getElementById("cc_cvv")?.value.trim();
        const errDiv = document.getElementById("card_errors");

        const showError = (msg) => {
            if (errDiv) { errDiv.textContent = msg; errDiv.style.display = "block"; }
            this.notification.add(msg, { type: "danger" });
            throw new Error(msg);
        };

        if (!ccNum || !ccMonth || !ccYear || !ccCvv) {
            showError(_t("Please fill in all required card fields."));
        }

        const providerId = this.model.root.data.provider_id?.[0];
        if (!providerId) {
            showError(_t("Please select a payment provider first."));
        }

        const [provider] = await this.orm.read(
            "payment.provider",
            [providerId],
            ["authorize_login", "authorize_client_key", "state"]
        );

        const acceptJSUrl = provider.state === "enabled"
            ? "https://js.authorize.net/v1/Accept.js"
            : "https://jstest.authorize.net/v1/Accept.js";

        await loadJS(acceptJSUrl);

        await new Promise((resolve, reject) => {
            let attempts = 0;
            const interval = setInterval(() => {
                attempts++;
                if (typeof Accept !== "undefined" && typeof Accept.dispatchData === "function") {
                    clearInterval(interval);
                    resolve();
                } else if (attempts >= 50) {
                    clearInterval(interval);
                    reject(new Error(_t("Accept.js failed to initialize. Please refresh and try again.")));
                }
            }, 100);
        });

        const secureData = {
            authData: {
                apiLoginID: provider.authorize_login,
                clientKey: provider.authorize_client_key,
            },
            cardData: {
                cardNumber: ccNum,
                month: ccMonth,
                year: ccYear,
                cardCode: ccCvv,
            },
        };

        await new Promise((resolve, reject) => {
            Accept.dispatchData(secureData, (response) => {
                if (response.messages.resultCode === "Error") {
                    let msg = "";
                    response.messages.message.forEach(m => msg += `${m.code}: ${m.text}\n`);
                    if (errDiv) { errDiv.textContent = msg; errDiv.style.display = "block"; }
                    this.notification.add(msg.trim(), { type: "danger" });
                    reject(new Error(msg));
                    return;
                }
                if (errDiv) errDiv.style.display = "none";
                this.model.root.update({
                    opaque_data_descriptor: response.opaqueData.dataDescriptor,
                    opaque_data_value: response.opaqueData.dataValue,
                });
                resolve();
            });
        });
    },
});