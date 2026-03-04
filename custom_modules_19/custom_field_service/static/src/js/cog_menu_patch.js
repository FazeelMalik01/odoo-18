/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, xml } from "@odoo/owl";

export class PrintPDFButton extends Component {
    static template = xml`
        <button type="button" class="dropdown-item" t-on-click="onClick">
            <i class="fa fa-file-pdf-o me-2"/>
            Print PDF
        </button>
    `;
    
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async onClick(ev) {
        ev.stopPropagation();
        const selectedResIds = this.env.searchModel.getSelectedResIds();
        
        if (!selectedResIds.length) {
            this.notification.add(
                "Please select at least one task.",
                { type: "warning" }
            );
            return;
        }

        try {
            const action = await this.orm.call(
                "project.task",
                "action_print_pdf",
                [selectedResIds],
                { context: this.env.searchModel.context }
            );
            
            if (action) {
                this.actionService.doAction(action);
            }
        } catch (error) {
            this.notification.add(
                "Error generating PDF: " + (error.message || "Unknown error"),
                { type: "danger" }
            );
        }
    }
}

// Register the button in the cog menu for project.task model
export const PrintPDFCogMenuItem = {
    Component: PrintPDFButton,
    isDisplayed: ({ config, searchModel }) => {
        return (
            searchModel.resModel === "project.task" &&
            config.viewType === "list"
        );
    },
    groupNumber: 20,
    isAction: true,
};

registry.category("cogMenu").add("custom_field_service_print_pdf", PrintPDFCogMenuItem, {
    sequence: 15,
});
