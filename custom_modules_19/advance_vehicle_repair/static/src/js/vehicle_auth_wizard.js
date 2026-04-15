import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted } from "@odoo/owl";

class KioskRedirectAction extends Component {
    static template = "advance_vehicle_repair.KioskRedirect";

    setup() {
        this.actionService = useService("action");
        this.menuService = useService("menu");

        onMounted(async () => {
            const params = this.props.action.params;

            // Get the kiosk child menu object
            const menu = this.menuService.getMenu(params.menu_id);

            // Force switch active root menu — Odoo 19 confirmed method
            if (menu) {
                this.menuService.setCurrentMenu(menu);
            }

            // Now open the action
            await this.actionService.doAction(
                'advance_vehicle_repair.vehicle_repair_services_line_action_kiosk',
                {
                    clearBreadcrumbs: true,
                    additionalContext: {
                        ...params.context,
                        authenticated_employee_id: params.authenticated_employee_id,
                    },
                }
            );
        });
    }
}

KioskRedirectAction.props = ["action", "*"];
registry.category("actions").add("kiosk_redirect", KioskRedirectAction);