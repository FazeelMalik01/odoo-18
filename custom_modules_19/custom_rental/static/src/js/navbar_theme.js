import { NavBar } from "@web/webclient/navbar/navbar";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export const RENTAL_APP_XMLID = "sale_renting.rental_menu_root";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        const menuService = useService("menu");

        useEffect(
            () => {
                const app = menuService.getCurrentApp();
                const isRental = app?.xmlid === RENTAL_APP_XMLID;
                document.body.classList.toggle("o_rental_theme", isRental);
                return () => document.body.classList.remove("o_rental_theme");
            },
            () => [menuService.getCurrentApp()?.id]
        );
    },

    get isRentalApp() {
        return this.currentApp?.xmlid === RENTAL_APP_XMLID;
    },

    get rentalBrandLogoUrl() {
        const cid = user.activeCompany?.id;
        return cid ? `/web/image/res.company/${cid}/logo` : "";
    },
});
