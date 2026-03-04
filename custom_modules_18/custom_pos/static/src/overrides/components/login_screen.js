/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

setTimeout(() => {
    const LoginScreen = registry.category("pos_screens").get("LoginScreen");

    if (!LoginScreen) {
        console.warn("CUSTOM POS: LoginScreen not found!");
        return;
    }

    console.log("CUSTOM POS: Patching LoginScreen Back button behavior");

    patch(LoginScreen.prototype, {
        async clickBack() {
            console.log("CUSTOM POS: clickBack override executed");

            // Call POS HR selectCashier but ignore which employee is returned
       if (!this.pos.config.module_pos_hr) {
            super.clickBack();
            return;
        }

        if (this.pos.login) {
            this.state.pin = "";
            this.pos.login = false;
        } else {
            const employee = await this.selectCashier();
            if (employee) {
                this.pos.closePos(); // closes POS and goes to backend
                // super.clickBack();
                return;
            }
        }
            return super.clickBack();
        },
    });
}, 50);
