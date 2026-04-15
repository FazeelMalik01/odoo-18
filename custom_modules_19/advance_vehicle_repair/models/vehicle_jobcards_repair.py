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
    quantity = fields.Float(string="Quantity", default=1.0)
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    service_cost = fields.Float(string="Service Cost", default=0.0)

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

    current_employee_id = fields.Many2one('hr.employee', string="Current Employee Timer")

    from_bundle = fields.Boolean(string="Added From Bundle", default=False)
    from_spare = fields.Boolean(string="Added From Spare Part", default=False)

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

    @api.onchange('service_id')
    def _onchange_service_cost(self):
        if self.service_id:
            self.service_cost = self.service_id.service_amount

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
    
    def _get_current_employee(self):
        # Only trust context if came via PIN wizard
        employee_id = self.env.context.get('authenticated_employee_id')
        if employee_id:
            return self.env['hr.employee'].browse(employee_id)
        return None  # DO NOT fall back to env.user here

    def action_start_timer(self):
        self.ensure_one()

        assigned_employees = self.assigners.mapped('employee_id')

        # Route 1: Came via PIN wizard — context has authenticated_employee_id
        if self.env.context.get('authenticated_employee_id'):
            current_employee = self._get_current_employee()
            if current_employee and current_employee in assigned_employees:
                self._start_employee_timer(current_employee)
                return
            else:
                raise ValidationError(_("Authenticated employee is not assigned to this task."))

        if len(assigned_employees) == 1:
            self._start_employee_timer(assigned_employees[0])
            return

        # Multiple assigners — must open wizard to select who
        return self._open_technician_wizard()
    
    def _open_technician_wizard(self):
        assigned_employees = self.assigners.mapped('employee_id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Select Technician',
            'res_model': 'repair.technician.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_repair_line_id': self.id,
                'allowed_employee_ids': assigned_employees.ids,  # restrict dropdown
            }
        }
    
    def _start_employee_timer(self, employee):
        self.ensure_one()
        self.timer_start = fields.Datetime.now()
        self.is_timer_running = True
        self.state = 'in_progress'
        self.current_employee_id = employee.id

    def action_pause_timer(self):
        self.ensure_one()

        if not self.is_timer_running or not self.timer_start:
            return

        self._ensure_analytic_account()

        end_time = fields.Datetime.now()
        duration = (end_time - self.timer_start).total_seconds() / 3600.0

        self.timer_start = False
        self.is_timer_running = False

        # Same logic — PIN context or env.user
        employee = self._get_current_employee() or self.current_employee_id

        if not employee:
            raise ValidationError(_("Cannot determine the technician for this timesheet entry."))

        self.env['account.analytic.line'].create({
            'name': self.title,
            'employee_id': employee.id,
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
    
    def write(self, vals):
        res = super().write(vals)

        if 'state' in vals and vals.get('state') == 'done':
            for rec in self:
                service = rec.service_id

                if service and service.is_recurring and service.recurring_days:
                    done_date = rec.end_date or fields.Date.today()
                    next_date = done_date + timedelta(days=service.recurring_days)

                    self.env['vehicle.service.reminder'].create({
                        'customer_id': rec.jobcard_id.customer_id.id,
                        'jobcard_id': rec.jobcard_id.id,
                        'service_id': service.id,
                        'done_date': done_date,
                        'next_due_date': next_date,
                        'recurring_days': service.recurring_days,
                    })

        return res
class VehicleRepairPartsLine(models.Model):
    _name = 'vehicle.repair.parts.line'
    _description = "Vehicle Repair Spare Parts"
    _inherit = ['product.catalog.mixin']
    jobcard_id = fields.Many2one('vehicle.jobcard', string="Job card Id")

    spare_id = fields.Many2one('product.product', string='Spare Part', domain="[('id','in',spare_domain)]")
    quantity = fields.Integer(string="Quantity", default=1)
    unit_price = fields.Float(string="Unit Price", compute='_compute_unit_price', store=True)
    sub_total = fields.Float(string="Sub Total", compute='_compute_sub_total', store=True)

    # For Currency Symbol Display
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True, tracking=True)

    #Consumption
    consume = fields.Boolean(string="Consumed")

    from_bundle = fields.Boolean(string="Added From Bundle", default=False)
    
    spare_domain = fields.Many2many(
        'product.product',
        compute='_compute_spare_domain'
    )

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
    
    @api.onchange('jobcard_id.brand_id', 'jobcard_id.model_id', 'jobcard_id.filter_spare_parts')
    def _compute_spare_domain(self):
        for line in self:
            if line.jobcard_id.filter_spare_parts and line.jobcard_id.brand_id and line.jobcard_id.model_id:
                line.spare_domain = self.env['product.product'].search([
                    ('spare_part', '=', True),
                    ('vehicle_compatibility_ids.make_id', '=', line.jobcard_id.brand_id.id),
                    ('vehicle_compatibility_ids.model_id', '=', line.jobcard_id.model_id.id)
                ])
            else:
                line.spare_domain = self.env['product.product'].search([('spare_part', '=', True)])
    @api.readonly
    def action_add_from_catalog(self):
        # Get the parent jobcard from context
        jobcard = self.env['vehicle.jobcard'].browse(
            self.env.context.get('order_id')  # 'order_id' key is standard in catalog mixin
        )
        return jobcard.with_context(
            child_field='repair_parts_line'  # your O2M field name on jobcard
        ).action_add_from_catalog()

    def _get_product_catalog_lines_data(self, **kwargs):
        if len(self) == 1:
            return {
                'quantity': self.quantity,
                'price': self.unit_price,
                'readOnly': False,
                'uomDisplayName': self.spare_id.uom_id.display_name if self.spare_id else '',
            }
        elif self:
            self.spare_id.ensure_one()
            return {
                'readOnly': True,
                'price': self[0].unit_price,
                'quantity': sum(self.mapped('quantity')),
                'uomDisplayName': self.spare_id.uom_id.display_name,
            }
        else:
            return {
                'quantity': 0,
            }

class VechicleRepairImage(models.Model):
    _name = 'vehicle.repair.image'
    _description = 'Vehicle Repair Images'
    _rec_name = 'note'

    image = fields.Binary(string='Image', tracking=True)
    note = fields.Text(string="Description")
    jobcard_id = fields.Many2one('vehicle.jobcard', string="Job card Id")

