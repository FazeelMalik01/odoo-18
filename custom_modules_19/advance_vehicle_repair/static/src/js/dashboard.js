/* @odoo-module */

import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { useService } from '@web/core/utils/hooks';
import { Layout } from "@web/search/layout";
import { uniqueId } from "@web/core/utils/functions";
import { loadBundle } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { ensureJQuery } from "@web/core/ensure_jquery";

export class AdvanceVehicleRepairDashboard extends Component {
    static props = ["*"];
    static template = 'advance_vehicle_repair.dashboard';

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.barChartRef = useRef("barChart");
        this.pieChartRef = useRef("pieChart");
        this.customerSearchRef = useRef("customerSearchContainer");
        this.customerSearchTimeout = null;
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            'total_bookings': 0,
            'total_bookings_ids': [],
            'total_customers': 0,
            'total_customers_ids': [],
            'total_teams': 0,
            'total_teams_ids': [],
            'total_inspection_jobcards': 0,
            'total_inspection_jobcards_ids': [],
            'total_repair_jobcards': 0,
            'total_repair_jobcards_ids': [],
            'total_job_cards': 0,
            'total_job_cards_ids': [],
            'total_todays_bookings': 0,
            'total_todays_bookings_ids': [],
            'groupby_advance_vehicle_repair': [],
            'customer_search': '',
            'customer_search_results': [],
            'customer_dropdown_visible': false,
            'customer_menu_open_id': null,
            'customer_menu_open_customer': null,
            'customer_menu_position': { top: 0, left: 0 },
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.fetch_data();
        });

        onMounted(async () => {
            await ensureJQuery();
            await this.render_graphs();
            this._boundCloseCustomerDropdown = this._closeCustomerDropdownOnClickOutside.bind(this);
            document.addEventListener('click', this._boundCloseCustomerDropdown);
        });

        onWillUnmount(() => {
            document.removeEventListener('click', this._boundCloseCustomerDropdown);
            if (this.customerSearchTimeout) {
                clearTimeout(this.customerSearchTimeout);
            }
        });
    }

    _closeCustomerDropdownOnClickOutside(ev) {
        if (this.customerSearchRef.el && !this.customerSearchRef.el.contains(ev.target)) {
            this.state.customer_dropdown_visible = false;
            this.state.customer_menu_open_id = null;
            this.state.customer_menu_open_customer = null;
        }
    }

    async fetch_data () {
        var self = this;
        var result = await rpc('/advance_vehicle_repair/dashboard_data',{
            user_id: session.uid || false,
        });

        self.state.total_bookings = result.total_bookings;
        self.state.total_bookings_ids = result.total_bookings_ids;

        self.state.total_customers = result.total_customers;
        self.state.total_customers_ids = result.total_customers_ids;

        self.state.total_teams = result.total_teams;
        self.state.total_teams_ids = result.total_teams_ids;

        self.state.total_inspection_jobcards = result.total_inspection_jobcards;
        self.state.total_inspection_jobcards_ids = result.total_inspection_jobcards_ids;

        self.state.total_repair_jobcards = result.total_repair_jobcards;
        self.state.total_repair_jobcards_ids = result.total_repair_jobcards_ids;

        self.state.total_job_cards = result.total_job_cards;
        self.state.total_job_cards_ids = result.total_job_cards_ids;

        self.state.total_todays_bookings = result.total_todays_bookings;
        self.state.total_todays_bookings_ids = result.total_todays_bookings_ids;

        self.state.groupby_advance_vehicle_repair = result.groupby_advance_vehicle_repair;
    }

    render_graphs () {
        var self = this;
        var bar_chart_id = uniqueId('chart_');
        $(this.barChartRef.el).empty();
        var $canvasBarChartContainer = $('<div/>', {class: 'o_graph_bar_canvas_container'});
        this.$canvasBarChart = $('<canvas/>').attr('id', bar_chart_id);
        $canvasBarChartContainer.append(this.$canvasBarChart);
        $(this.barChartRef.el).append($canvasBarChartContainer);

        var bar_labels = []
        var bar_data = []
        for (var i = 0; i < self.state.groupby_advance_vehicle_repair.length; i++) {
            if (self.state.groupby_advance_vehicle_repair[i].model_name){
                bar_labels.push(self.state.groupby_advance_vehicle_repair[i].model_name);
                if (self.state.groupby_advance_vehicle_repair[i].model_name_count){
                    bar_data.push(self.state.groupby_advance_vehicle_repair[i].model_name_count)
                }else{
                    bar_data.push(0)
                }
            }
        };

        var ctxBar = this.$canvasBarChart[0];
        this.chartBar = new Chart(ctxBar, {
            type: 'bar',
            data: {
                labels: bar_labels,
                datasets: [
                    {
                        label: "Vehicle Model(Count)",
                        backgroundColor: self.getbgcolor(bar_labels.length),
                        data: bar_data
                    }
                ],
            },
            options: {
                legend: { display: false },
                title: {
                    display: true,
                    text: 'Vehicle Model (Count)'
                },
                scales: {
                    y: {
                        ticks: {
                            display: false,
                        }
                    }
                }
            }
        });

        var pie_chart_id = uniqueId('chart_');
        $(this.pieChartRef.el).empty();
        var $canvasPieChartContainer = $('<div/>', {class: 'o_graph_pie_canvas_container'});
        this.$canvasPieChart = $('<canvas/>').attr('id', pie_chart_id);
        $canvasPieChartContainer.append(this.$canvasPieChart);
        $(this.pieChartRef.el).append($canvasPieChartContainer);

        var ctxPie = this.$canvasPieChart[0];
        this.chartPie = new Chart(ctxPie, {
            type: 'pie',
            data: {
                labels: [
                    "Total Inspections",
                    "Total Repairs",
                    "Total Repairs & Inspections",
                ],
                datasets: [{
                    label: "Job cards",
                    backgroundColor: ["#3e95cd", "#8e5ea2", "#3cba9f", "#e8c3b9"],
                    data: [
                        self.state.total_inspection_jobcards,
                        self.state.total_repair_jobcards,
                        self.state.total_job_cards,
                    ]
                }],
            },
            options: {
                responsive: true,
                title: {
                    display: true,
                    text: 'Job card Analysis'
                },
            },
        });
    }

    getbgcolor (length) {
        var self = this;
        var colors = ["#3e95cd", "#8e5ea2", "#3cba9f", "#e8c3b9", "#c45850"];
        var color = [];
        var length = length;
        for (var i = 0; i < length; i++) {
            for (var j = 0; j < colors.length; j++) {
                color.push(colors[Math.abs(j - i)]);
            }
        }
        return color;
    }
    onCustomerSearchInput(ev) {
        this.state.customer_search = ev.target.value;
        if (this.customerSearchTimeout) {
            clearTimeout(this.customerSearchTimeout);
        }
        const term = (ev.target.value || '').trim();
        if (term.length < 1) {
            this.state.customer_search_results = [];
            this.state.customer_dropdown_visible = false;
            this.state.customer_menu_open_id = null;
            this.state.customer_menu_open_customer = null;
            return;
        }
        this.state.customer_menu_open_id = null;
        this.state.customer_menu_open_customer = null;
        this.customerSearchTimeout = setTimeout(() => this.fetchCustomerSuggestions(term), 300);
    }

    async fetchCustomerSuggestions(term) {
        try {
            const results = await rpc('/advance_vehicle_repair/search_customers', { term, limit: 15 });
            this.state.customer_search_results = results || [];
            this.state.customer_dropdown_visible = this.state.customer_search_results.length > 0;
        } catch {
            this.state.customer_search_results = [];
            this.state.customer_dropdown_visible = false;
        }
    }

    onCustomerSearchKeydown(ev) {
        if (ev.key === 'Enter') {
            ev.preventDefault();
            if (this.state.customer_search_results.length === 1) {
                this.onSelectCustomer(this.state.customer_search_results[0]);
            } else {
                this.onCustomerSearch();
            }
        } else if (ev.key === 'Escape') {
            this.state.customer_dropdown_visible = false;
            this.state.customer_menu_open_id = null;
            this.state.customer_menu_open_customer = null;
        }
    }

    onCustomerSearch() {
        const term = (this.state.customer_search || '').trim();
        const domain = term
            ? ['|', ['name', 'ilike', term], '|', ['phone', 'ilike', term], ['vehicle_ids.registration_no', 'ilike', term]]
            : [];
        this.state.customer_dropdown_visible = false;
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            name: 'Customers',
            domain: domain,
            views: [[false, 'list'], [false, 'form']],
            context: { search_default_customer: 1 },
        }, {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        });
    }

    onSelectCustomer(customer) {
        this.state.customer_search = '';
        this.state.customer_search_results = [];
        this.state.customer_dropdown_visible = false;
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            name: customer.name || 'Customer',
            res_id: customer.id,
            views: [[false, 'form']],
        }, {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        });
    }

    getCustomerMenuStyle() {
        const p = this.state.customer_menu_position;
        return `position: fixed; z-index: 1060; top: ${p.top}px; left: ${p.left}px;`;
    }

    toggleCustomerMenu(customer, ev) {
        if (this.state.customer_menu_open_id === customer.id) {
            this.state.customer_menu_open_id = null;
            this.state.customer_menu_open_customer = null;
            return;
        }
        const el = ev && ev.currentTarget;
        if (el) {
            const rect = el.getBoundingClientRect();
            const menuWidth = 140;
            this.state.customer_menu_position = {
                top: rect.bottom + 2,
                left: Math.max(4, rect.right - menuWidth),
            };
        }
        this.state.customer_menu_open_id = customer.id;
        this.state.customer_menu_open_customer = customer;
    }

    async onOpenBooking(customer) {
    this.state.customer_search = '';
    this.state.customer_search_results = [];
    this.state.customer_dropdown_visible = false;
    this.state.customer_menu_open_id = null;
    this.state.customer_menu_open_customer = null;

    const action = await this.orm.call(
        'vehicle.booking',
        'action_create_booking_from_customer',
        [customer.id]
    );

    this.actionService.doAction(action, {
        on_reverse_breadcrumb: this.on_reverse_breadcrumb,
    });
    }


    onOpenJobCard(customer) {
        this.state.customer_search = '';
        this.state.customer_search_results = [];
        this.state.customer_dropdown_visible = false;
        this.state.customer_menu_open_id = null;
        this.state.customer_menu_open_customer = null;
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'jobcard.booking.type.wizard',
            name: 'Select Booking Type',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: { default_customer_id: customer.id },
        }, {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        });
    }

    onDashboardAction(ev){
        ev.preventDefault();
        var self = this;

        var $currentTarget = $(ev.currentTarget);
        var $action = $currentTarget.data('action');

        var domain = []

        if ($action === 'total_bookings'){
            console.log("yes")
            domain.push(['id', 'in', self.state.total_bookings_ids])
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'vehicle.booking',
                name: 'Licensing Management',
                domain: domain,
                views: [[false, 'list'],[false, 'form']],
            }, {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb
            });
        }
        else if ($action === 'total_customers'){
            domain.push(['id', 'in', self.state.total_customers_ids])
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'res.partner',
                name: 'Licensing Management',
                domain: domain,
                views: [[false, 'list'],[false, 'form']],
            }, {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb
            });
        }
        else if ($action === 'total_teams'){
            domain.push(['id', 'in', self.state.total_teams_ids])
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'vehicle.teams',
                name: 'Licensing Management',
                domain: domain,
                views: [[false, 'list'],[false, 'form']],
            }, {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb
            });
        }

        else if ($action === 'total_job_cards'){
            domain.push(['id', 'in', self.state.total_job_cards_ids])
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'vehicle.jobcard',
                name: 'Licensing Management',
                domain: domain,
                views: [[false, 'list'],[false, 'form']],
            }, {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb
            });
        }

        else if ($action === 'total_inspection_jobcards'){
            domain.push(['id', 'in', self.state.total_inspection_jobcards_ids])
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'vehicle.jobcard',
                name: 'Licensing Management',
                domain: domain,
                views: [[false, 'list'],[false, 'form']],
            }, {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb
            });
        }
        else if ($action === 'total_repair_jobcards'){
            domain.push(['id', 'in', self.state.total_repair_jobcards_ids])
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'vehicle.jobcard',
                name: 'Licensing Management',
                domain: domain,
                views: [[false, 'list'],[false, 'form']],
            }, {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb
            });
        }
        else if ($action === 'total_todays_bookings'){
            domain.push(['id', 'in', self.state.total_todays_bookings_ids])
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'vehicle.booking',
                name: 'Vehicle Repair Management',
                domain: domain,
                views: [[false, 'list'],[false, 'form']],
            }, {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb
            });
        }
    }
}
AdvanceVehicleRepairDashboard.components = {
    Layout,
}

registry.category('actions').add('advance_vehicle_repair.dashboard', AdvanceVehicleRepairDashboard);

