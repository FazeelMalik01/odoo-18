import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, useState, xml } from "@odoo/owl";

const RES_MODEL = "password.entry";

export class PasswordViewCopyWidget extends Component {
    static template = xml`
        <div class="o_row d-flex align-items-center flex-wrap gap-2 o_password_actions_row">
            <input t-att-type="state.isRevealed ? 'text' : 'password'"
                   class="form-control"
                   readonly="readonly"
                   style="max-width: 20em;"
                   t-model="state.displayValue"
                   placeholder="********"
                   t-att-id="inputId"/>
            <button type="button"
                    class="btn btn-secondary"
                    t-on-click="onRevealClick"
                    title="Show / Hide password"
                    t-att-disabled="!canRevealCopy ? true : undefined">
                <span t-esc="state.isRevealed ? '🙈' : '👁'"/>
            </button>
            <button type="button"
                    class="btn btn-secondary"
                    t-on-click="onCopyClick"
                    title="Copy to clipboard"
                    t-att-disabled="!canRevealCopy ? true : undefined">
                📋
            </button>
        </div>
    `;

    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            displayValue: "",
            isRevealed: false,
        });
        this.inputId = "password_field_" + (this.props.record?.id ?? Math.random().toString(36).slice(2));
    }

    get canRevealCopy() {
        const r = this.props.record;
        return r && !r.isNew && typeof r.resId === "number";
    }

    async onRevealClick() {
        if (!this.canRevealCopy) {
            this.notification.add("Save the entry first, then use Reveal or Copy.", { type: "warning" });
            return;
        }
        if (this.state.isRevealed) {
            this.state.displayValue = "";
            this.state.isRevealed = false;
            return;
        }
        try {
            const password = await this.orm.call(
                RES_MODEL,
                "action_reveal_password",
                [[this.props.record.resId]]
            );
            this.state.displayValue = password || "";
            this.state.isRevealed = true;
        } catch (e) {
            this.notification.add(e?.message || "Could not reveal password", { type: "danger" });
        }
    }

    async onCopyClick() {
        if (!this.canRevealCopy) {
            this.notification.add("Save the entry first, then use Reveal or Copy.", { type: "warning" });
            return;
        }
        try {
            const password = await this.orm.call(
                RES_MODEL,
                "action_copy_password",
                [[this.props.record.resId]]
            );
            if (password) {
                await navigator.clipboard.writeText(password);
                this.notification.add("Password copied to clipboard", { type: "success" });
            } else {
                this.notification.add("No password set", { type: "warning" });
            }
        } catch (e) {
            this.notification.add(e?.message || "Could not copy password", { type: "danger" });
        }
    }
}

export const passwordViewCopyWidget = {
    component: PasswordViewCopyWidget,
};

registry.category("view_widgets").add("password_view_copy", passwordViewCopyWidget);
