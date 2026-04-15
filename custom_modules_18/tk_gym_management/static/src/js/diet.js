/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { session } from "@web/session";
import { Domain } from "@web/core/domain";
import { sprintf } from "@web/core/utils/strings";

const { Component, useSubEnv, useState, onMounted, onWillStart, useRef } = owl;
import { loadJS, loadCSS } from "@web/core/assets"

class DietDashboard extends Component {
  setup() {
//    this.rpc = useService("rpc");
    this.action = useService("action");
    this.orm = useService("orm");

    this.state = useState({
      dietData: {
        'members': 0,
        'leads': 0,
        'opportunities': 0,
        'diet_plans': 0,
        'diet_plan_templates': 0,
        'invoice_count': 0
      },
      invoiceStatus: { 'x-axis': [], 'y-axis': [] },
    });
    useSubEnv({
      config: {
        ...getDefaultConfig(),
        ...this.env.config,
      },
    });

    this.invoiceStatus = useRef('payment_month');
    this.genderDietPlan = useRef('gender_diet_plan');

    onWillStart(async () => {
      let dietStats = await this.orm.call('diet.dashboard', 'get_diet_stats', []);
      if (dietStats) {
        this.state.dietData = dietStats;
        this.state.invoiceStatus = { 'x-axis': dietStats['invoices'][0], 'y-axis': dietStats['invoices'][1] }
      }
    });
    onMounted(() => {
      this.getInvoiceStatusGraph();
      this.renderGenderDietPlan(this.genderDietPlan.el, this.state.dietData);
    })
  }
  viewStatistic(type) {
    let name = this.getTitleName(type);
    let model = this.getModelName(type);
    let domain = this.getDomain(type)
    this.action.doAction({
      type: 'ir.actions.act_window',
      name: name,
      res_model: model,
      view_mode: 'list',
      views: [[false, 'list'], [false, 'form']],
      target: 'current',
      domain: domain,
      context: { 'create': false },
    });
  }

  getDomain(type) {
    let domain = []
    if (type === 't_members') {
      domain = [['is_member', '=', true]]
    } else if (type === 'web_leads') {
      domain = [['type', '=', 'lead'], ['is_form_website', '=', true]]
    } else if (type === 'web_opportunities') {
      domain = [['type', '=', 'opportunity'], ['is_form_website', '=', true]]
    } else if (type === 't_diet_plans') {
      domain = []
    } else if (type === 't_diet_plan_templates') {
      domain = []
    } else if (type === 't_invoices') {
      domain = [['diet_plan_id', '!=', false]]
    }
    return domain
  }

  getModelName(type) {
    let model = ""
    if (type === 't_members') {
      model = 'res.partner'
    } else if (type === 'web_leads') {
      model = 'crm.lead'
    } else if (type === 'web_opportunities') {
      model = 'crm.lead'
    } else if (type === 't_diet_plans') {
      model = 'diet.plan'
    } else if (type === 't_diet_plan_templates') {
      model = 'diet.plan.template'
    } else if (type === 't_invoices') {
      model = 'account.move'
    }
    return model
  }

  getTitleName(type) {
    let name = ""
    if (type === 't_members') {
      name = 'Members'
    } else if (type === 'web_leads') {
      name = 'Leads'
    } else if (type === 'web_opportunities') {
      name = 'Opportunities'
    } else if (type === 't_diet_plans') {
      name = 'Diet Plans'
    } else if (type === 't_diet_plan_templates') {
      name = 'Diet Plan Templates'
    } else if (type === 't_invoices') {
      name = 'Invoices'
    }
    return name
  }

  renderGraph(el, options) {
    const graphData = new ApexCharts(el, options);
    graphData.render();
  }

  getInvoiceStatusGraph() {
    const options = {
      series: [{
        name: "Total Payment",
        data: this.state.invoiceStatus['y-axis'],
      }],
      chart: {
        height: 450,
        type: 'line',
        zoom: {
          enabled: false
        }
      },
      dataLabels: {
        enabled: false
      },
      stroke: {
        curve: 'straight'
      },
      title: {
        align: 'left'
      },
      grid: {
        row: {

          opacity: 0.5
        },
      },
      xaxis: {
        categories: this.state.invoiceStatus['x-axis'],
      },
      fill: {
        type: 'gradient',
        gradient: {
          shade: 'dark',
          gradientToColors: ['#FDD835'],
          shadeIntensity: 1,
          type: 'horizontal',
          opacityFrom: 1,
          opacityTo: 1,
          stops: [0, 100, 100, 100]
        },
      }
    };
    this.renderGraph(this.invoiceStatus.el, options);
  }

  renderGenderDietPlan(div, sessionData) {
    let root = am5.Root.new(div);
    root.setThemes([
      am5themes_Animated.new(root)
    ]);

    const chart = root.container.children.push(am5percent.PieChart.new(root, {
      layout: root.verticalLayout,
      radius: am5.percent(80),
      innerRadius: am5.percent(50),

    }));

    let series = chart.series.push(am5percent.PieSeries.new(root, {
      valueField: "value",
      categoryField: "category",
      alignLabels: false,

    }));
    series.get("colors").set("colors", [
      am5.color("#93d1f7"),
      am5.color("#edbde9"),
      am5.color("#95c7c7")
    ]);

    series.labels.template.setAll({
      textType: "circular",
      centerX: 0,
      centerY: 0,
    });

    series.slices.template.set("tooltipText", "{category}: {value}");

    series.data.setAll([
      { value: sessionData['gender_diet_plan'][0], category: "Male" },
      { value: sessionData['gender_diet_plan'][1], category: "Female" },
      { value: sessionData['gender_diet_plan'][2], category: "Other" },
    ]);


    const legend = chart.children.push(am5.Legend.new(root, {
      centerX: am5.percent(50),
      x: am5.percent(50),
      marginTop: 15,
      marginBottom: 15,
    }));

    legend.data.setAll(series.dataItems);

    series.appear(1000, 100);

  }
}
DietDashboard.template = "tk_gym_management.diet_dashboard";
registry.category("actions").add("diet_dashboard", DietDashboard);
