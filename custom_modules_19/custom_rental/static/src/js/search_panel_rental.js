import { SearchPanel } from "@web/search/search_panel/search_panel";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";

function markRentalSearchPanelLabels(rootEl) {
    if (!rootEl || !document.body.classList.contains("o_rental_theme")) {
        return;
    }
    rootEl.querySelectorAll(".o_search_panel_label_title").forEach((el) => {
        const t = (el.textContent || "").trim();
        if (t === "Fully Invoiced" || t.includes("Fully Invoiced")) {
            el.classList.add("o_rental_fully_invoiced_label");
        } else {
            el.classList.remove("o_rental_fully_invoiced_label");
        }
        if (t === "Green") {
            el.classList.add("o_rental_health_sidebar_green");
        } else {
            el.classList.remove("o_rental_health_sidebar_green");
        }
        if (t === "Yellow") {
            el.classList.add("o_rental_health_sidebar_yellow");
        } else {
            el.classList.remove("o_rental_health_sidebar_yellow");
        }
        if (t === "Red") {
            el.classList.add("o_rental_health_sidebar_red");
        } else {
            el.classList.remove("o_rental_health_sidebar_red");
        }
    });
}

patch(SearchPanel.prototype, {
    setup() {
        super.setup(...arguments);
        const run = () => {
            const el = this.root?.el;
            if (el) {
                markRentalSearchPanelLabels(el);
            }
        };
        onMounted(run);
        onPatched(run);
    },
});
