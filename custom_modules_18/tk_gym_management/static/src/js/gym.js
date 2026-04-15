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

class GymDashboard extends Component {
  setup() {
//    this.rpc = useService("rpc");
    this.action = useService("action");
    this.orm = useService("orm");

    this.state = useState({
      gymData: { 'members': 0, 'memberships': 0, 'equipments': 0, 'workout': 0, 'exercise': 0, 'classes': 0 },
      getMembership: { 'x-axis': [], 'y-axis': [] },
      getMembershipPerson: { 'membership': [], 'membership_counts': [], 'membership_counts_f': [] },
      getDailyAttendance: { 'months': [], 'employees': [], 'members': [] },
      invoiceStatus: { 'x-axis': [], 'y-axis': [] },
    });

    useSubEnv({
      config: {
        ...getDefaultConfig(),
        ...this.env.config,
      },
    });

    this.getMembership = useRef('membership_categories');
    this.getMembershipPerson = useRef('membership_person');
    this.getDailyAttendance = useRef('attendance');
    this.invoiceStatus = useRef('payment_month');

    onWillStart(async () => {
      let gymManagementData = await this.orm.call('memberships.member', 'get_gym_stats', []);
      if (gymManagementData) {
        this.state.gymData = gymManagementData;
        this.state.getMembership = { 'x-axis': gymManagementData['get_membership'][0], 'y-axis': gymManagementData['get_membership'][1] };
        this.state.getMembershipPerson = { 'membership': gymManagementData['membershipperson'][0], 'membership_counts': gymManagementData['membershipperson'][1], 'membership_counts_f': gymManagementData['membershipperson'][2] };
        this.state.getDailyAttendance = { 'months': gymManagementData['daily_attendance'][0], 'employees': gymManagementData['daily_attendance'][1], 'members': gymManagementData['daily_attendance'][2] };
        this.state.invoiceStatus = { 'x-axis': gymManagementData['invoice'][0], 'y-axis': gymManagementData['invoice'][1] }
      }
    });
    onMounted(() => {
      this.renderGetMembershipGraph(this.getMembership.el, this.state.getMembership);
      this.getMembershipPersonGraph(this.getMembershipPerson.el, this.state.getMembershipPerson);
      this.getDailyAttendanceGraph();
      this.getInvoiceStatusGraph();
    })
  }

  viewGymMembers() {
    let domain = [['is_member', '=', true]];
    let context = { 'create': false }
    this.action.doAction({
      type: 'ir.actions.act_window',
      name: 'Members',
      res_model: 'res.partner',
      domain: domain,
      view_mode: 'kanban',
      views: [[false, 'kanban'], [false, 'list'], [false, 'form'], [false, 'activity']],
      target: 'current',
      context: context,
    });
  }

  viewGymMemberships() {
    let context = { 'create': false }
    this.action.doAction({
      type: 'ir.actions.act_window',
      name: 'Memberships',
      res_model: 'memberships.member',
      views: [[false, 'list'], [false, 'form'], [false, 'pivot'], [false, 'activity']],
      target: 'current',
      context: context,
    });
  }

  viewGymEquipments() {
    let context = { 'create': false }
    this.action.doAction({
      type: 'ir.actions.act_window',
      name: 'Equipments',
      res_model: 'gym.equipment',
      views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
      target: 'current',
      context: context,
    });
  }

  viewGymWorkout() {
    let context = { 'create': false }
    this.action.doAction({
      type: 'ir.actions.act_window',
      name: 'Workouts',
      res_model: 'gym.workout',
      views: [[false, 'kanban'], [false, 'list'], [false, 'form'], [false, 'activity']],
      target: 'current',
      context: context,
    });
  }

  viewGymExercise() {
    let context = { 'create': false }
    this.action.doAction({
      type: 'ir.actions.act_window',
      name: 'Exercises',
      res_model: 'gym.exercise',
      views: [[false, 'kanban'], [false, 'list'], [false, 'form'], [false, 'activity']],
      target: 'current',
      context: context,
    });
  }

  viewGymClasses() {
    let context = { 'create': false }
    this.action.doAction({
      type: 'ir.actions.act_window',
      name: 'Yoga Classes',
      res_model: 'gym.class',
      views: [[false, 'list'], [false, 'form'], [false, 'calendar'], [false, 'activity']],
      target: 'current',
      context: context,
    });
  }

  renderGraph(el, options) {
    const graphData = new ApexCharts(el, options);
    graphData.render();
  }

  renderGetMembershipGraph(div, sessionData) {
    let root = am5.Root.new(div);
    let chartData = []

    root.setThemes([
      am5themes_Animated.new(root)
    ]);

    let chart = root.container.children.push(am5percent.PieChart.new(root, {
      layout: root.verticalLayout,
      innerRadius: am5.percent(50)
    }));

    let series = chart.series.push(am5percent.PieSeries.new(root, {
      valueField: "value",
      categoryField: "category",
      alignLabels: false
    }));

    series.get("colors").set("colors", [
      am5.color("#f29494"),
      am5.color("#c6ace3"),
      am5.color("#f5c6a2"),
      am5.color("#8bc9c6"),
      am5.color("#d9d9b2")
    ]);
    series.labels.template.setAll({
      textType: "circular",
      centerX: 0,
      centerY: 0
    });

    for (var i = 0; i < sessionData['x-axis'].length; i++) {
      chartData.push({
        value: sessionData['y-axis'][i],
        category: sessionData['x-axis'][i],
      });
    }
    series.data.setAll(chartData);
    series.slices.template.set("tooltipText", "{category}: {value}");
    let legend = chart.children.push(am5.Legend.new(root, {
      centerX: am5.percent(50),
      x: am5.percent(50),
      marginTop: 15,
      marginBottom: 15,
    }));

    legend.data.setAll(series.dataItems);

    series.appear(1000, 100);
  }


  getMembershipPersonGraph(div, sessionData) {
    var root = am5.Root.new(div);
    let chartData = []


    var myTheme = am5.Theme.new(root);

    myTheme.rule("Grid", ["base"]).setAll({
      strokeOpacity: 0.1
    });

    root.setThemes([
      am5themes_Animated.new(root),
      myTheme
    ]);

    var chart = root.container.children.push(am5xy.XYChart.new(root, {
      panX: false,
      panY: false,
      wheelX: "panY",
      wheelY: "zoomY",
      paddingLeft: 0,
      layout: root.verticalLayout
    }));

    chart.set("scrollbarY", am5.Scrollbar.new(root, {
      orientation: "vertical"
    }));

    for (var i = 0; i < sessionData['membership'].length; i++) {
      chartData.push({
        "year": sessionData['membership'][i],
        "male": sessionData['membership_counts'][i],
        "female": sessionData['membership_counts_f'][i],
      });
    }

    var yRenderer = am5xy.AxisRendererY.new(root, {});
    var yAxis = chart.yAxes.push(am5xy.CategoryAxis.new(root, {
      categoryField: "year",
      renderer: yRenderer,
      tooltip: am5.Tooltip.new(root, {})
    }));

    yRenderer.grid.template.setAll({
      location: 1
    })

    yAxis.data.setAll(chartData);

    var xAxis = chart.xAxes.push(am5xy.ValueAxis.new(root, {
      min: 0,
      maxPrecision: 0,
      renderer: am5xy.AxisRendererX.new(root, {
        minGridDistance: 40,
        strokeOpacity: 0.1
      })
    }));

    var legend = chart.children.push(am5.Legend.new(root, {
      centerX: am5.p50,
      x: am5.p50
    }));

    function makeSeries(name, fieldName, color) {
      var series = chart.series.push(am5xy.ColumnSeries.new(root, {
        name: name,
        stacked: true,
        xAxis: xAxis,
        yAxis: yAxis,
        baseAxis: yAxis,
        stroke: am5.color(0xffffff),
        strokeWidth: 1,
        valueXField: fieldName,
        categoryYField: "year"
      }));

      series.columns.template.setAll({
        tooltipText: "{name}, {categoryY}: {valueX}",
        tooltipY: am5.percent(90)
      });
      series.data.setAll(chartData);

      series.appear();

      series.bullets.push(function () {
        return am5.Bullet.new(root, {
          sprite: am5.Label.new(root, {
            fill: root.interfaceColors.get("alternativeText"),
            centerY: am5.p50,
            centerX: am5.p50,
            populateText: true
          })
        });
      });
      series.columns.template.setAll({ fill: color });


      legend.data.push(series);
    }

    makeSeries("Male", "male", am5.color("#93d1f7"));
    makeSeries("Female", "female", am5.color("#edbde9"));

    chart.appear(1000, 100);
  }


  getDailyAttendanceGraph() {
    const options = {
      series: [{
        name: 'Employees',
        data: this.state.gymData['daily_attendance'][0][1],
      }, {
        name: 'Members',
        data: this.state.gymData['daily_attendance'][0][2]
      }],
      chart: {
        type: 'bar',
        height: 450,
        stacked: true,
        toolbar: {
          show: true
        },
        zoom: {
          enabled: true
        }
      },
      colors: ["#66CCCC", "#FFCC99"],
      plotOptions: {
        bar: {
          horizontal: false,
          borderRadius: 10,
          dataLabels: {
            total: {
              enabled: true,
              style: {
                fontSize: '13px',
                fontWeight: 900
              }
            }
          }
        },
      },
      xaxis: {
        categories: this.state.gymData['daily_attendance'][0][0],
        labels: {
          rotate: -70
        }
      },
      legend: {
        position: 'bottom',
      },
      fill: {
        opacity: 1
      }
    };
    //    this.renderGraph(this.getDailyAttendance.el, options);
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

}
GymDashboard.template = "tk_gym_management.gym_management_dashboard";
registry.category("actions").add("gym_dashboard", GymDashboard);