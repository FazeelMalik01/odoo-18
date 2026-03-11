from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class VehicleJobcard(models.Model):
    _name = 'vehicle.jobcard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Vehicle Jobcard'
    _rec_name = 'sequence_id'
    _order = "id desc"

    sequence_id = fields.Char(string='Inspection No', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('quality_check', 'Quality Check'),
        ('on_delivery', 'Ready for Delivery'),
        ('delivered', 'Delivered'),
        ('sale_order', 'Sale Order'),
        ('closed', 'Closed'),
        ('cancel', 'Cancelled')],
        default='new', string='State')
    vehicle_source = fields.Selection([
        ('fleet', ' Vehicle From Fleet'),
        ('register', 'Vehicle From Register')
    ], default='register', store=True)
    booking_type = fields.Selection([
        ('vehicle_inspection', 'Vehicle Inspection'),
        ('vehicle_repair', 'Vehicle Repair'),
        ('both', 'Vehicle Inspection + Repair')
    ], string="Booking Type", default='vehicle_inspection', tracking=True)

    booking_id = fields.Many2one('vehicle.booking', string='Booking ID', ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order ID')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True,
                                  tracking=True)
    responsible_id = fields.Many2one('res.users', string='Responsible', tracking=True, default=lambda self: self.env.user, domain="[('share', '=', False), ('company_ids', 'in', company_id)]")
    booking_date = fields.Date(string='Date', default=fields.Date.today, required=True, store=True)

    # Customer Details
    customer_id = fields.Many2one('res.partner', string="Customer", required=True, store=True)
    street = fields.Char(string='Street', store=True)
    street2 = fields.Char(string='Street2', store=True)
    city = fields.Char(string='City', store=True)
    pin_code = fields.Char(string='Pin', store=True)
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', store=True)
    phone = fields.Char(string='Phone', store=True)
    email = fields.Char(string='Email', store=True)

    # Vehicle Details
    vehicle_register_id = fields.Many2one('vehicle.register', string="Vehicle", required=False, tracking=True,  domain="[('customer_id', '=', customer_id), ('state', '=', 'active')]")
    brand_id = fields.Many2one('vehicle.brand', string='Vehicle Brand', required=True, store=True)
    model_id = fields.Many2one('vehicle.model', string='Vehicle Model', required=True, store=True,
                               domain="[('brand_id', '=', brand_id)]")
    registration_no = fields.Char(string="Registration No")
    fuel_type_id = fields.Many2one('vehicle.fuel.type', string='Vehicle Fuel', store=True)
    vin_no = fields.Char(string='VIN No', store=True)
    transmission_type = fields.Selection([
        ('manual', "Manual"),
        ('automatic', "Automatic"),
        ('cvt', "CVT")
    ], string='Transmission Type', default='manual', store=True)
    kilometer = fields.Float(string='Current Kilometer')
    inspection_type = fields.Selection([
        ('full_inspection', 'Full Inspection'),
        ('specific_inspection', 'Specific Inspection')
    ], string="Type of Inspection", default="specific_inspection", store=True)
    model_year = fields.Many2one('vehicle.model.year', string="Model Year")
    is_part_assessment = fields.Boolean(string="Part Assessment", default=True)
    is_inner_body_inspection = fields.Boolean(string="Inner Body Inspection", default=True)
    is_outer_body_inspection = fields.Boolean(string="Outer Body Inspection")
    is_tyre_inspection = fields.Boolean(string="Tyre Inspection")
    is_mechanical_condition = fields.Boolean(string="Mechanical Condition")
    is_vehicle_component = fields.Boolean(string="Vehicle Component", default=True)
    is_vehicle_fluid = fields.Boolean(string="Vehicle Fluid")
    inspector_id = fields.Many2one('hr.employee', string="Inspected By", tracking=True)
    # inspection_amount = fields.Float(string="Inspection Charge", compute='_compute_inspection_amount', store=True,currency_field="company_currency")
    inspection_amount = fields.Float(string="Inspection Charge",store=True,currency_field="company_currency")
    # Inspection Notebook
    parts_assessment_ids = fields.Many2many('vehicle.parts.assessments', 'vehicle_jobcard_assessments_rel',
                                                    'jobcard_id', 'assessment_id', string="Assessments")
    inner_condition_ids = fields.One2many('vehicle.jobcard.inner.condition', 'jobcard_id',
                                        string='Inner Body Condition')
    outer_condition_ids = fields.One2many("vehicle.jobcard.outer.condition", "jobcard_id",
                                        string='Outer Body Condition')
    mechanical_ids = fields.One2many('vehicle.jobcard.mechanical.condition', 'jobcard_id',
                                             string='Mechanical Condition')
    components_ids = fields.One2many('vehicle.jobcard.components', 'jobcard_id', string='Vehicle Components')
    fluid_ids = fields.One2many('vehicle.jobcard.fluids', "jobcard_id", string="Fluids Condition")
    tyre_ids = fields.One2many('vehicle.jobcard.tyre.condition', 'jobcard_id', string='Tyre Condition')
    image_ids = fields.One2many('vehicle.jobcard.inspection.image', 'jobcard_id', string='Inspection Images')

    checklist_ids = fields.Many2many('vehicle.checklist', 'vehicle_jobcard_checkist_rel', 'jobcard_id',
                                               'checklist_id', string="Checklist Template")
    checklist_lines = fields.One2many('vehicle.checklist.line', 'jobcard_id', string="Checklist Lines")

        # NOTEBOOK 2
    review_notes = fields.Text(string="Review Notes")

        # NOTEBOOK 3
    service_ids = fields.One2many('vehicle.repair.services.line', 'jobcard_id', string="Job Card Service")
    total_service_charge = fields.Float(string="Service Charges", compute='_compute_total_service_charge', store=True)
    parts_ids = fields.One2many('vehicle.repair.parts.line', 'jobcard_id', string="Job Card Spare Parts")
    total_parts_charge = fields.Float(string="Spare Parts Price", compute='_compute_total_parts_charge', store=True)
    total_cost = fields.Float(string="Total", compute="_compute_total_cost", store=True)
    repair_image_ids = fields.One2many('vehicle.repair.image', 'jobcard_id', string="Repairing Images")


        # NOTEBOOK 4
    signed_by = fields.Char(string="Signed By")
    signature_date = fields.Datetime(string="Signed On")
    signature_img = fields.Binary(string="Signature")

        # NOTEBOOK 5
    observations = fields.Text(string='Customer Observations', tracking=True)

    sale_order_count = fields.Integer(string="Sale Orders", compute='_compute_sale_count')
    task_count = fields.Integer(string="Task", compute='_compute_task_count')

    #Technicians
    technician_ids = fields.Many2many('res.partner', string="Technicians", compute="_compute_technicians", store=True)

    #bundle
    bundle_id = fields.Many2one('auto.service.bundle')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence_id', _('New')) == _('New'):
                vals['sequence_id'] = self.env['ir.sequence'].next_by_code('vehicle.jobcard') or _('New')
        return super(VehicleJobcard, self).create(vals_list)


    def write(self, vals):
        for record in self:
            if vals.get('state') == 'new':
                if record.state in ('delivered', 'sale_order', 'closed'):
                    raise ValidationError(
                        "You cannot revert the job card to 'New' once it's delivered, invoiced, or closed.")

                if record.sale_order_id:
                    if record.sale_order_id.invoice_status in ('invoiced', 'upselling'):
                        raise ValidationError("You cannot revert to 'New' as this job card has been invoiced.")

                    invoices = record.sale_order_id.invoice_ids.filtered(lambda inv: inv.state == 'posted')
                    if any(inv.payment_state == 'paid' for inv in invoices):
                        raise ValidationError("You cannot revert to 'New' as this job card has been fully paid.")

        return super(VehicleJobcard, self).write(vals)

    def button_confirm(self):
        self.ensure_one()
        self.state = 'confirmed'

    def button_in_progress(self):
        self.ensure_one()
        self.state = 'in_progress'

    def button_hold(self):
        self.ensure_one()
        self.state = 'on_hold'

    def button_un_hold(self):
        self.ensure_one()
        self.state = 'in_progress'

    def button_quality_check(self):
        self.ensure_one()

        # If inspector not selected → open wizard
        if self.booking_type != 'vehicle_repair' and not self.inspector_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Select Inspector',
                'res_model': 'select.inspector.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_jobcard_id': self.id,
                }
            }

        # Service validation
        if self.booking_type != 'vehicle_inspection':
            if any(service.state not in ('done', 'cancel') for service in self.service_ids):
                raise ValidationError(
                    "All services must be 'Done' or in 'Cancel' state before Quality Check."
                )

        self.state = 'quality_check'

    def button_on_delivery(self):
        self.ensure_one()
        self.state = 'on_delivery'

    def button_delivered(self):
        self.ensure_one()
        self.state = 'delivered'

    def button_closed(self):
        pass

    def button_cancel(self):
        self.ensure_one()
        self.state = 'cancel'

    def button_draft(self):
        self.ensure_one()
        self.state = 'new'

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        if self.customer_id:

            # Patch customer info
            self.street = self.customer_id.street or ''
            self.street2 = self.customer_id.street2 or ''
            self.city = self.customer_id.city or ''
            self.pin_code = self.customer_id.zip or ''
            self.state_id = self.customer_id.state_id.id or False
            self.country_id = self.customer_id.country_id.id or False
            self.phone = self.customer_id.phone or ''
            self.email = self.customer_id.email or ''

            # ❗ Only reset vehicle fields if the user manually cleared vehicle
            if not self.env.context.get('default_vehicle_register_id') and not self.vehicle_register_id:
                self.brand_id = False
                self.model_id = False
                self.registration_no = False
                self.fuel_type_id = False
                self.vin_no = False
                self.transmission_type = False
                self.kilometer = False
                self.model_year = False

        else:
            self.street = ''
            self.street2 = ''
            self.city = ''
            self.pin_code = ''
            self.state_id = False
            self.country_id = False
            self.phone = ''
            self.email = ''

            self.vehicle_register_id = False
            self.brand_id = False
            self.model_id = False
            self.registration_no = False
            self.fuel_type_id = False
            self.vin_no = False
            self.transmission_type = False
            self.model_year = False

    @api.onchange('vehicle_register_id')
    def _onchange_vehicle_register_id(self):
        if self.vehicle_register_id:

            vehicle = self.vehicle_register_id

            self.brand_id = vehicle.brand_id.id
            self.model_id = vehicle.model_id.id
            self.registration_no = vehicle.registration_no
            self.fuel_type_id = vehicle.fuel_type_id.id
            self.vin_no = vehicle.vin_no
            self.transmission_type = vehicle.transmission_type
            self.kilometer = vehicle.kilometer
            self.model_year = vehicle.model_year

        else:
            self.brand_id = False
            self.model_id = False
            self.registration_no = False
            self.fuel_type_id = False
            self.vin_no = False
            self.transmission_type = False
            self.kilometer = False
            self.model_year = False

    def _compute_sale_count(self):
        for record in self:
            record.sale_order_count = self.env['sale.order'].search_count([('jobcard_id', '=', record.id)])

    @api.depends('service_ids')
    def _compute_task_count(self):
        for record in self:
            record.task_count = self.env['vehicle.repair.services.line'].search_count([('jobcard_id', '=', record.id)])

    # Smart Button for Sale Order with list view and form view
    def action_sale_order(self):
        sale_order_ids = self.env['sale.order'].search([('jobcard_id', '=', self.id)]).ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Orders',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', sale_order_ids)],
            'target': 'current',
        }

    # Smart Button for Task view with list view and form view
    def action_view_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tasks',
            'res_model': 'vehicle.repair.services.line',
            'view_mode': 'list,form',
            'domain': [('jobcard_id', '=', self.id)],
            'target': 'current',
        }


    # Inspection Functions
    @api.onchange('checklist_ids')
    def _onchange_checklist_ids(self):
        if self.checklist_ids:
            self.checklist_lines = [(5, 0, 0)]
            new_lines = []
            for checklist in self.checklist_ids:
                new_lines.append((0, 0, {
                    'display_type': 'line_section',
                    'name': checklist.name,
                }))

                checklist_lines = self.env['vehicle.checklist.line'].sudo().search([
                    ('checklist_id', 'in', checklist.ids),
                    ('display_type', '!=', 'line_section')
                ])

                for line in checklist_lines:
                    new_lines.append((0, 0, {
                        'display_type': 'line_item',
                        'is_checked': False,
                        'name': line.name,
                    }))
            self.checklist_lines = new_lines
        else:
            self.checklist_lines = [(5, 0, 0)]


    #Repair Functions

    @api.depends('service_ids.service_cost', 'service_ids.state')
    def _compute_total_service_charge(self):
        for record in self:
            total_charge = sum(line.service_cost for line in record.service_ids if line.state == 'done')
            record.total_service_charge = total_charge

    @api.depends('parts_ids.sub_total')
    def _compute_total_parts_charge(self):
        for record in self:
            total_charge = sum(line.sub_total for line in record.parts_ids)
            record.total_parts_charge = total_charge

    @api.depends('total_service_charge', 'total_parts_charge', 'inspection_amount')
    def _compute_total_cost(self):
        for record in self:
            service = record.total_service_charge or 0.0
            parts = record.total_parts_charge or 0.0
            inspection = record.inspection_amount or 0.0
            print(' service',service)
            print(' parts',parts)
            print(' inspection',inspection)

            record.total_cost = service + parts + inspection
            print(' total_cost',  record.total_cost)

    def button_sale_order(self):

        if not self.sale_order_id:
            raise UserError("Please create quotation first.")

        sale_order = self.sale_order_id

        # Remove old lines
        sale_order.order_line.unlink()

        order_lines = []

        for line in self.service_ids:
            if line.state == 'done':
                order_lines.append((0, 0, {
                    'product_id': line.service_id.product_id.id,
                    'product_uom_qty': 1,
                    'price_unit': line.service_cost,
                    'name': line.service_id.name,
                }))

        for line in self.parts_ids:
            order_lines.append((0, 0, {
                'product_id': line.spare_id.id,
                'product_uom_qty': line.quantity,
                'price_unit': line.unit_price,
            }))

        sale_order.write({'order_line': order_lines})

        # Confirm
        sale_order.action_confirm()

        self.state = 'sale_order'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
            'target': 'current',
        }

    
    #Quotation
    def button_quotation(self):
        if self.booking_type == 'vehicle_inspection':
            self.state = 'new'
            inspection_product = self.env.ref('advance_vehicle_repair.product_inspection_1')
            sale_order = self.env['sale.order'].create({
                'partner_id': self.customer_id.id,
                'origin': self.sequence_id,
                'jobcard_id': self.id,
            })
            sale_order_lines = [(0, 0, {
                'product_id': inspection_product.id,
                'product_uom_qty': 1,
                'price_unit': self.inspection_amount,
            })]
            sale_order.order_line = sale_order_lines
            self.sale_order_id = sale_order.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sale Order',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': sale_order.id,
                'target': 'current',
            }
        elif self.booking_type == 'vehicle_repair':
            self.state = 'new'
            sale_order = self.env['sale.order'].create({
                'partner_id': self.customer_id.id,
                'origin': self.sequence_id,
                'jobcard_id': self.id,
            })

            # Prepare service order lines
            service_order_lines = []
            for line in self.service_ids:
                    service_order_lines.append((0, 0, {
                        'product_id': line.service_id.product_id.id,
                        'product_uom_qty': 1,
                        'price_unit': line.service_cost,
                        'name': line.service_id.name,
                        'product_uom_id': line.service_id.product_id.uom_id.id,
                    }))

            # Prepare parts order lines
            parts_order_lines = []
            for line in self.parts_ids:
                parts_order_lines.append((0, 0, {
                    'product_id': line.spare_id.id,
                    'product_uom_qty': line.quantity,
                    'price_unit': line.unit_price,
                    'product_uom_id': line.spare_id.uom_id.id,
                }))

            sale_order.order_line = service_order_lines + parts_order_lines
            self.sale_order_id = sale_order.id

            return {
                'type': 'ir.actions.act_window',
                'name': 'Sale Order',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': sale_order.id,
                'target': 'current',
            }
        elif self.booking_type == 'both':
            self.state = 'new'
            inspection_product = self.env.ref('advance_vehicle_repair.product_inspection_1')

            sale_order = self.env['sale.order'].create({
                'partner_id': self.customer_id.id,
                'origin': self.sequence_id,
                'jobcard_id': self.id,
            })

            # Prepare Inspection order lines
            inspection_order_lines = [(0, 0, {
                'product_id': inspection_product.id,
                'product_uom_qty': 1,
                'price_unit': self.inspection_amount,
            })]

            # Prepare service order lines
            service_order_lines = []
            for line in self.service_ids:
                    service_order_lines.append((0, 0, {
                        'product_id': line.service_id.product_id.id,
                        'product_uom_qty': 1,
                        'price_unit': line.service_cost,
                        'name': line.service_id.name,
                        'product_uom_id': line.service_id.product_id.uom_id.id,
                    }))

            # Prepare parts order lines
            parts_order_lines = []
            for line in self.parts_ids:
                parts_order_lines.append((0, 0, {
                    'product_id': line.spare_id.id,
                    'product_uom_qty': line.quantity,
                    'price_unit': line.unit_price,
                    'product_uom_id': line.spare_id.uom_id.id,
                }))

            sale_order.order_line = inspection_order_lines + service_order_lines + parts_order_lines
            self.sale_order_id = sale_order.id

            return {
                'type': 'ir.actions.act_window',
                'name': 'Sale Order',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': sale_order.id,
                'target': 'current',
            }

    @api.model
    def action_open_booking_type_wizard(self, *args, **kwargs):
        """Open the booking type wizard when clicking New from list/kanban/pivot/activity.
        The wizard then opens the jobcard form with default_booking_type set."""
        return self.env.ref('advance_vehicle_repair.action_jobcard_booking_type_wizard').read()[0]

    @api.depends('service_ids.assigners')
    def _compute_technicians(self):
        for record in self:
            partners = record.service_ids.mapped('assigners.employee_id.work_contact_id')
            record.technician_ids = [(6, 0, partners.ids)]

    
    @api.constrains('kilometer')
    def _check_and_update_kilometer(self):
        for record in self:
            if record.vehicle_register_id:
                current_km = record.vehicle_register_id.kilometer or 0
                # Validation: new km cannot be lower
                if record.kilometer < current_km:
                    raise ValidationError(
                        f"New kilometer ({record.kilometer}) cannot be lower than current vehicle kilometer ({current_km})!"
                    )
                # Only add log if kilometer increased
                if record.kilometer > current_km:
                    # Update vehicle register km
                    record.vehicle_register_id.kilometer = record.kilometer
    
    @api.onchange('parts_ids')
    def _onchange_parts_ids_add_service(self):
        for jobcard in self:
            existing_services = jobcard.service_ids.mapped('service_id.id')

            commands = []

            for line in jobcard.parts_ids:
                spare_product = line.spare_id

                if spare_product.linked_service_id and spare_product.linked_service_id.id not in existing_services:
                    commands.append((0, 0, {
                        'service_id': spare_product.linked_service_id.id,
                    }))

            if commands:
                jobcard.service_ids = commands

    
    @api.onchange('bundle_id')
    def _onchange_bundle_id(self):
        """Populate services and spare parts from selected bundle"""
        for jobcard in self:
            if not jobcard.bundle_id:
                continue

            service_commands = []
            spare_commands = []

            for line in jobcard.bundle_id.line_ids:
                if line.type == 'service' and line.service_id:
                    service_commands.append((0, 0, {
                        'service_id': line.service_id.id,
                    }))
                elif line.type == 'spare' and line.spare_id:
                    spare_commands.append((0, 0, {
                        'spare_id': line.spare_id.id,
                        'quantity': line.quantity,
                    }))

            # Replace existing lines with bundle lines (optional: can append instead)
            jobcard.service_ids = service_commands
            jobcard.parts_ids = spare_commands

    
    # @api.onchange('model_id', 'model_year')
    # def _onchange_model_spare_parts(self):
    #     """Populate spare parts lines based on selected vehicle model and year"""
    #     for jobcard in self:
    #         if not jobcard.model_id:
    #             jobcard.parts_ids = [(5, 0, 0)]  # clear lines if no model
    #             continue

    #         # Find all spare products compatible with this model and model year
    #         compatible_products = self.env['product.vehicle.compatibility'].search([
    #             ('model_id', '=', jobcard.model_id.id),
    #             ('model_year_ids', 'in', jobcard.model_year.id) if jobcard.model_year else ('id', '!=', 0)  # all years if not selected
    #         ])

    #         spare_products = compatible_products.mapped('product_id').filtered(lambda p: p.spare_part)

    #         # Create commands to add to parts_ids
    #         parts_commands = []
    #         for product in spare_products:
    #             parts_commands.append((0, 0, {
    #                 'spare_id': product.id,
    #                 'quantity': 1,
    #             }))

    #         # Replace current lines with these parts
    #         jobcard.parts_ids = parts_commands