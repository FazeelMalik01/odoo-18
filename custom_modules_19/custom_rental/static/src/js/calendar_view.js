/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";
import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

function isRentalCalendar(model) {
    return model.resModel === "sale.order" && !!model.meta?.context?.in_rental_app;
}

function styleRentalSaleOrderEvent(el, record, model) {
    if (!isRentalCalendar(model) || !record?.rawRecord) {
        return;
    }
    el.classList.remove("o_rental_cal_quote", "o_rental_cal_booked");
    const st = record.rawRecord.state;
    const main = el.querySelector(".fc-event-main");
    if (st === "draft" || st === "sent") {
        el.classList.add("o_rental_cal_quote");
        el.style.border = "1px solid #e6c800";
        el.style.color = "#111111";
        if (main) {
            main.style.color = "#111111";
        }
    } else if (st === "sale" || st === "done") {
        el.classList.add("o_rental_cal_booked");
        el.style.color = "#ffffff";
        if (main) {
            main.style.color = "#ffffff";
        }
    }
}

patch(CalendarSidePanel.prototype, {
    get rentalQuoteFollowUps() {
        const model = this.props.model;
        if (!isRentalCalendar(model)) {
            return [];
        }
        const now = DateTime.now().startOf("day");
        const items = [];
        for (const r of Object.values(model.records)) {
            const raw = r.rawRecord;
            if (!raw || !["draft", "sent"].includes(raw.state)) {
                continue;
            }
            const partner = raw.partner_id;
            const label = Array.isArray(partner) ? partner[1] : "";
            if (!label) {
                continue;
            }
            let daysLate = 0;
            if (raw.rental_start_date) {
                const start = DateTime.fromISO(`${raw.rental_start_date}`.substring(0, 10)).startOf(
                    "day"
                );
                if (start.isValid && start < now) {
                    daysLate = Math.floor(now.diff(start, "days").days);
                }
            }
            if (daysLate === 0 && raw.date_order) {
                const d = DateTime.fromISO(`${raw.date_order}`.replace(" ", "T")).startOf("day");
                if (d.isValid) {
                    const age = Math.floor(now.diff(d, "days").days);
                    if (age >= 3) {
                        daysLate = age;
                    }
                }
            }
            if (daysLate > 0) {
                items.push({ id: raw.id, label, daysLate });
            }
        }
        items.sort((a, b) => b.daysLate - a.daysLate);
        return items.slice(0, 12);
    },
});

patch(CalendarCommonRenderer.prototype, {
    onEventDidMount(info) {
        super.onEventDidMount(info);
        const record = this.props.model.records[info.event.id];
        styleRentalSaleOrderEvent(info.el, record, this.props.model);
    },
});

patch(CalendarYearRenderer.prototype, {
    onEventDidMount(info) {
        super.onEventDidMount(info);
        const record = this.props.model.records[info.event.id];
        styleRentalSaleOrderEvent(info.el, record, this.props.model);
    },
});

patch(CalendarController.prototype, {
    setup() {
        super.setup(...arguments);
        this._actionService = useService("action");
    },
    openRentalPos() {
        try {
            localStorage.removeItem("rental_pos_state");
        } catch (_) {
            /* ignore private mode / quota */
        }
        this._actionService.doAction({
            type: "ir.actions.client",
            tag: "rental_pos_page",
            name: "Rental POS",
            context: { rental_pos_fresh_categories: true },
        });
    },
    /**
     * Open Rental POS on the payment step with the order loaded instead of the sale order form.
     */
    async editRecord(record, context = {}) {
        if (isRentalCalendar(this.model) && record.id) {
            return this._actionService.doAction({
                type: "ir.actions.client",
                tag: "rental_pos_page",
                name: "Rental POS",
                context: {
                    ...context,
                    rental_pos_sale_order_id: record.id,
                    rental_pos_initial_page: "payment",
                },
            });
        }
        return super.editRecord(record, context);
    },
});
