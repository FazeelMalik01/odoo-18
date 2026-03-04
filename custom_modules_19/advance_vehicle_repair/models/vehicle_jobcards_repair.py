from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class VehicleRepairServicesLine(models.Model):
    _name = 'vehicle.repair.services.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Vehicle Repair Line"
    _rec_name = 'service_id'

    jobcard_id = fields.Many2one('vehicle.jobcard', string="Job card Id", ondelete='cascade')
    service_id = fields.Many2one('vehicle.services', string="Service")
    product_id = fields.Many2one('product.product', string='Product', store=True)
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    service_cost = fields.Float(string="Service Cost", compute='_compute_service_amount', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
        ], default="draft", tracking=True, store=True)
    title = fields.Char(string="Title", compute='_compute_title', store=True, readonly=False, tracking=True)
    assigners = fields.Many2many('vehicle.teams.line', string="Assigners", domain="[('id', 'in', team_employee_ids)]",store=True)
    assigners_user_ids = fields.Many2many('res.users', string="Assigners User IDs",compute="_compute_assigners_user_ids", store=True)
    service_team = fields.Many2one('vehicle.teams', string="Service Team", compute='_compute_service_team', store=True, readonly=False)
    team_employee_ids = fields.One2many(related='service_team.team_employee_ids', string="Team Employees", readonly=True)

    # Notebook
    customer_id = fields.Many2one(related='jobcard_id.customer_id', string="Customer", store=True)
    brand_id = fields.Many2one(related='jobcard_id.brand_id', string="Brand", store=True)
    model_id = fields.Many2one(related='jobcard_id.model_id', string="Model", store=True)
    fuel_type_id = fields.Many2one(related='jobcard_id.fuel_type_id', string="Fuel Type", store=True)
    registration_no = fields.Char(related='jobcard_id.registration_no', string="Registration No", store=True)
    vin_no = fields.Char(related='jobcard_id.vin_no', string="VIN No", store=True)
    note = fields.Text(string='Note')

    # For Currency Symbol Display
    company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    responsible_id = fields.Many2one('res.users', string='Responsible', tracking=True, default=lambda self: self.env.user, domain="[('share', '=', False), ('company_ids', 'in', company_id)]")

    #Timesheet
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False)
    timer_start = fields.Datetime(string="Timer Start")
    is_timer_running = fields.Boolean(string="Timer Running", default=False)
    timesheet_ids = fields.One2many('account.analytic.line', 'repair_line_id', string="Timesheets")
    total_duration = fields.Float(string="Total Hours", compute="_compute_total_duration", store=True)

    # spare parts
    parts_ids = fields.One2many(related='jobcard_id.parts_ids', string="Spare Parts", readonly=False)

    @api.depends('assigners')
    def _compute_assigners_user_ids(self):
        for record in self:
            user_ids = record.assigners.mapped('employee_id.user_id')
            record.assigners_user_ids = [(6, 0, user_ids.ids)]

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date and record.end_date < record.start_date:
                raise ValidationError("End Date cannot be earlier than Start Date.")

    @api.depends('service_id')
    def _compute_product_id(self):
        for record in self:
            record.product_id = record.service_id.product_id

    @api.depends('service_id')
    def _compute_service_team(self):
        for record in self:
            record.service_team = record.service_id.service_team_id

    @api.depends('service_id')
    def _compute_title(self):
        for record in self:
            record.title = record.service_id.name

    @api.depends('service_id')
    def _compute_service_amount(self):
        for record in self:
            record.service_cost = record.service_id.service_amount

    def action_progress(self):
        self.ensure_one()
        self.state = 'in_progress'

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'

    def action_service_task(self):
        self.ensure_one()
        return {
            'name': _('Repair Task'),
            'view_mode': 'form',
            'res_model': 'vehicle.repair.services.line',
            'domain': [],
            'res_id': self.id,
            'view_id': self.env.ref('advance_vehicle_repair.vehicle_repair_services_line_form').id,
            'type': 'ir.actions.act_window',
        }

    def action_service_assign(self):
        self.ensure_one()
        for record in self:
            if not record.service_id.service_team_id:
                raise ValidationError(f"You must add Service Team for the service: {record.service_id.name}.")
            team_employee_ids = record.service_id.service_team_id.mapped('team_employee_ids').ids
            record.assigners = [(6, 0, team_employee_ids)]
            record.state = 'assigned'

    @api.onchange('jobcard_id')
    def _onchange_jobcard_id(self):
        for line in self:
            if line.jobcard_id:
                # use booking_date if set, else use creation date of jobcard
                line.start_date = line.jobcard_id.booking_date or line.jobcard_id.create_date.date()
    
    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date:
            self.end_date = self.start_date
    
    #timesheet
    def _get_vehicle_repair_plan(self):
        plan = self.env['account.analytic.plan'].search([
            ('name', '=', 'Vehicle Repair'),
        ], limit=1)

        if not plan:
            plan = self.env['account.analytic.plan'].create({
                'name': 'Vehicle Repair',
            })

        return plan


    def _ensure_analytic_account(self):
        if not self.analytic_account_id:
            plan = self._get_vehicle_repair_plan()

            analytic = self.env['account.analytic.account'].create({
                'name': self.title or "Repair Task",
                'plan_id': plan.id,
            })

            self.analytic_account_id = analytic.id
    
    @api.depends('timesheet_ids.unit_amount')
    def _compute_total_duration(self):
        for record in self:
            record.total_duration = sum(record.timesheet_ids.mapped('unit_amount'))

    def action_start_timer(self):
        self.ensure_one()

        if not self.assigners_user_ids:
            raise ValidationError("Assign at least one user before starting the timer.")

        self.timer_start = fields.Datetime.now()
        self.is_timer_running = True
        self.state = 'in_progress'
    
    def action_pause_timer(self):
        self.ensure_one()

        if not self.is_timer_running or not self.timer_start:
            return

        self._ensure_analytic_account()

        end_time = fields.Datetime.now()
        duration = (end_time - self.timer_start).total_seconds() / 3600.0

        self.timer_start = False
        self.is_timer_running = False

        self.env['account.analytic.line'].create({
            'name': self.title,
            'user_id': self.env.user.id,
            'unit_amount': duration,
            'date': fields.Date.today(),
            'account_id': self.analytic_account_id.id,
            'repair_line_id': self.id,
            'company_id': self.company_id.id,
        })

    def action_complete(self):
        self.ensure_one()

        if self.is_timer_running:
            self.action_pause_timer()

        self.state = 'done'
class VehicleRepairPartsLine(models.Model):
    _name = 'vehicle.repair.parts.line'
    _description = "Vehicle Repair Spare Parts"

    jobcard_id = fields.Many2one('vehicle.jobcard', string="Job card Id")

    spare_id = fields.Many2one('product.product', string='Spare Part', domain=[('spare_part', '=', True)])
    quantity = fields.Integer(string="Quantity", default=1)
    unit_price = fields.Float(string="Unit Price", compute='_compute_unit_price', store=True)
    sub_total = fields.Float(string="Sub Total", compute='_compute_sub_total', store=True)

    # For Currency Symbol Display
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True, tracking=True)

    #Consumption
    consume = fields.Boolean(string="Consumed")

    @api.depends('spare_id.list_price')
    def _compute_unit_price(self):
        for record in self:
            record.unit_price = record.spare_id.list_price

    @api.depends('quantity', 'unit_price')
    def _compute_sub_total(self):
        for line in self:
            if line.unit_price:
                line.sub_total = line.unit_price * line.quantity
            else:
                line.sub_total = 0.0


class VechicleRepairImage(models.Model):
    _name = 'vehicle.repair.image'
    _description = 'Vehicle Repair Images'
    _rec_name = 'note'

    image = fields.Binary(string='Image', tracking=True)
    note = fields.Text(string="Description")
    jobcard_id = fields.Many2one('vehicle.jobcard', string="Job card Id")

