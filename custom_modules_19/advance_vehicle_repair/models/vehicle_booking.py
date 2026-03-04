import uuid
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class VehicleBookings(models.Model):
    _name = 'vehicle.booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Vehicle Bookings'
    _rec_name = 'sequence'
    _order = "id desc"


    def _get_default_access_token(self):
        return str(uuid.uuid4())

    sequence = fields.Char(string="Sequence No", required=True, copy=False, index=True, readonly=True, default=lambda self: _('New'))
    vehicle_source = fields.Selection([
        ('fleet', ' Vehicle From Fleet'),
        ('register', 'Vehicle From Register')
        ], default='register', tracking=True)
    vehicle_register_id = fields.Many2one('vehicle.register', string="Vehicle", required=False, tracking=True, domain="[('state', '=', 'active'), ('customer_id', '=', customer_id)]")
    vehicle_fleet_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=False, tracking=True)
    
    # Vehicle Details
    customer_id = fields.Many2one('res.partner', string="Customer", required=True, tracking=True)
    brand_id = fields.Many2one('vehicle.brand', string="Vehicle Brand", tracking=True)
    model_id = fields.Many2one('vehicle.model', string="Vehicle Model", tracking=True, domain="[('brand_id', '=', brand_id)]")
    model_name = fields.Char(related="model_id.name", store=True)
    fuel_type_id = fields.Many2one('vehicle.fuel.type', string="Fuel Type")
    registration_no = fields.Char(string="Registration No", tracking=True)
    vin_no = fields.Char(string="VIN No", tracking=True)
    transmission_type = fields.Selection([
        ('manual', "Manual"),
        ('automatic', "Automatic"),
        ('cvt', "CVT")
        ], string='Transmission Type', default='manual', tracking=True)
    
    # Address Details
    street = fields.Char(string="Street", tracking=True)
    street2 = fields.Char(string="Street2")
    city = fields.Char(string="City", tracking=True)
    pin_code = fields.Char(string="Pin", tracking=True)
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    phone = fields.Char(string="Phone", tracking=True)
    email = fields.Char(string="Email", tracking=True)

    # Booking Details
    booking_source = fields.Selection([
        ('direct', 'Direct'),
        ('portal', 'Portal'),
        ('website', 'Website'),
        ], string="Booking Source", default='direct', readonly=False)
    booking_type = fields.Selection([
        ('vehicle_inspection', 'Vehicle Inspection'),
        ('vehicle_repair', 'Vehicle Repair'),
        ('both', 'Vehicle Inspection + Repair')
        ], string="Booking Type", default='vehicle_inspection', tracking=True)
    booking_date = fields.Date(string="Booking Date", required=True, tracking=True, default=fields.Date.today)
    available_slot = fields.Many2one('vehicle.appointment.line', string="Booking Slot")

    currency_id = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    responsible_id = fields.Many2one('res.users', string='Responsible', tracking=True, domain="[('share', '=', False), ('company_ids', 'in', company_id)]")
    observations=fields.Text(string='Observations', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('create', 'Booking Created'),
        ('cancel', 'Cancelled')
        ], string="State", default="draft")
    jobcard_id = fields.Many2one('vehicle.jobcard', string='Job Card ID')
    access_token = fields.Char('Access Token', default=lambda self: self._get_default_access_token(), copy=False)
    access_url = fields.Char('Portal Access URL', compute='_compute_access_url', help='Contract Portal URL')

    vehicle_jobcard_count = fields.Integer("Inspection", compute='_compute_jobcard_count')
    customer_vehicle_ids = fields.Many2many(
        'vehicle.register',
        compute='_compute_customer_vehicle_ids',
        string="Customer's Vehicles",
        readonly=True,
    )

    @api.depends('customer_id')
    def _compute_customer_vehicle_ids(self):
        for record in self:
            if record.customer_id:
                record.customer_vehicle_ids = record.env['vehicle.register'].search([
                    ('customer_id', '=', record.customer_id.id),
                    ('state', '=', 'active')
                ])
            else:
                record.customer_vehicle_ids = record.env['vehicle.register']

    def _compute_jobcard_count(self):
        for record in self:
            record.vehicle_jobcard_count = self.env['vehicle.jobcard'].search_count([('booking_id', '=', record.id)])

    def button_open_jobcard(self):
        view = 'advance_vehicle_repair.action_vehicle_jobcard'
        action = self.env['ir.actions.act_window']._for_xml_id(view)
        action['view_mode'] = 'kanban,list,pivot,form,activity'
        action['domain'] = [('booking_id', 'in', self.ids)]
        action['context'] = {'active_test': False, 'create': False}
        return action
            
    @api.onchange('vehicle_register_id')
    def onchange_vehicle_register_id(self):
        if self.vehicle_register_id:
            self.customer_id = self.vehicle_register_id.customer_id.id or False
            self.brand_id = self.vehicle_register_id.brand_id.id or False
            self.model_id = self.vehicle_register_id.model_id.id or False
            self.fuel_type_id = self.vehicle_register_id.fuel_type_id.id or False
            self.transmission_type = self.vehicle_register_id.transmission_type or False
            self.registration_no = self.vehicle_register_id.registration_no or ''
            self.vin_no = self.vehicle_register_id.vin_no or ''
        else:
            self.customer_id = False
            self.brand_id = False
            self.model_id = False
            self.fuel_type_id = False
            self.transmission_type = False
            self.registration_no = ''
            self.vin_no = ''
    
    @api.onchange('vehicle_fleet_id')
    def onchange_vehicle_fleet_id(self):
        if self.vehicle_fleet_id:
            self.customer_id = self.vehicle_fleet_id.driver_id.id or False
            self.brand_id = False
            self.model_id = False
            self.fuel_type_id = False
            self.transmission_type = False
            self.registration_no = ''
            self.vin_no = self.vehicle_fleet_id.vin_sn or ''
        else:
            self.customer_id = False
            self.brand_id = False
            self.model_id = False
            self.fuel_type_id = False
            self.transmission_type = False
            self.registration_no = ''
            self.vin_no = ''

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        if self.customer_id:
            self.street = self.customer_id.street or ''
            self.street2 = self.customer_id.street2 or ''
            self.city = self.customer_id.city or ''
            self.pin_code = self.customer_id.zip or ''
            self.state_id = self.customer_id.state_id.id or False
            self.country_id = self.customer_id.country_id.id or False
            self.phone = self.customer_id.phone or ''
            self.email = self.customer_id.email or ''
            self.vehicle_register_id = False
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

    def vehicle_jobcard_button(self):
        for record in self:
            vehicle_jobcard = self.env['vehicle.jobcard'].create({
                'booking_id': record.id,
                'booking_type': record.booking_type,
                'customer_id': record.customer_id.id,
                'booking_date': record.booking_date,
                'brand_id': record.brand_id.id,
                'registration_no': record.registration_no,
                'model_id': record.model_id.id,
                'fuel_type_id': record.fuel_type_id.id,
                'vin_no': record.vin_no,
                'street': record.street,
                'street2': record.street2,
                'city': record.city,
                'state_id': record.state_id.id,
                'pin_code': record.pin_code,
                'state': 'new',
                'country_id': record.country_id.id,
                'phone': record.phone,
                'email': record.email,
                'transmission_type': record.transmission_type,
                'vehicle_source': record.vehicle_source,
                'observations': record.observations,
                'vehicle_register_id': record.vehicle_register_id.id
            })
            record.write({
                'jobcard_id': vehicle_jobcard.id,
                'state': 'create'
            })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Job Card',
                'res_model': 'vehicle.jobcard',
                'view_mode': 'form',
                'res_id': vehicle_jobcard.id,
                'view_id': self.env.ref('advance_vehicle_repair.vehicle_jobcard_form').id,
                'target': 'current'
            }

    def booking_cancel_button(self):
        self.state = 'cancel'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence', _('New')) == _('New'):
                vals['sequence'] = self.env['ir.sequence'].next_by_code('vehicle.booking') or _('New')
            if 'customer_id' in vals:
                customer = self.env['res.partner'].browse(vals['customer_id'])
                vals.update({
                    'street': customer.street or '',
                    'street2': customer.street2 or '',
                    'city': customer.city or '',
                    'pin_code': customer.zip or '',
                    'state_id': customer.state_id.id or False,
                    'country_id': customer.country_id.id or False,
                    'phone': customer.phone or '',
                    'email': customer.email or '',
                })
        record = super(VehicleBookings, self).create(vals_list)
        return record

    @api.onchange('booking_date')
    def _onchange_booking_date(self):
        if self.booking_date:
            day_of_week = self.booking_date.strftime("%A")
            appointment = self.env['vehicle.appointment'].search([('name', '=', day_of_week)], limit=1)
            if appointment:
                available_slots = self.env['vehicle.appointment.line'].search([('appointment_id', '=', appointment.id)])
                if available_slots:
                    return {'domain': {'available_slot': [('id', 'in', available_slots.ids)]}}
                else:
                    return {'domain': {'available_slot': []}}
            else:
                return {'domain': {'available_slot': []}}
        else:
            return {'domain': {'available_slot': []}}
        
    def get_portal_url(self, suffix=None, report_type=None, download=None, query_string=None, anchor=None):
        self.ensure_one()
        url = self.access_url + '%s?access_token=%s%s%s%s%s' % (
            suffix if suffix else '',
            self._portal_ensure_token(),
            '&report_type=%s' % report_type if report_type else '',
            '&download=true' if download else '',
            query_string if query_string else '',
            '#%s' % anchor if anchor else ''
        )
        return url
    
    def _portal_ensure_token(self):
        if not self.access_token:
            self.sudo().write({
                'access_token': str(uuid.uuid4())
            })
        return self.access_token
    
    def _compute_access_url(self):
        for record in self:
            record.access_url = '/my/vehicle_booking/%s' % record.id

    def _get_portal_return_action(self):
        self.ensure_one()
        return self.env.ref('advance_vehicle_repair.action_vehicle_booking')

    @api.constrains('vehicle_register_id', 'customer_id')
    def _check_vehicle_customer_match(self):
        for record in self:
            if record.vehicle_register_id:
                if record.vehicle_register_id.customer_id != record.customer_id:
                    raise ValidationError(
                        _("The selected vehicle does not belong to the selected customer.")
                    )

                if record.vehicle_register_id.state != 'active':
                    raise ValidationError(
                        _("You cannot select an inactive vehicle.")
                    )

    @api.model
    def action_create_booking_from_customer(self, customer_id):
        booking = self.create({
            'customer_id': customer_id,
        })

        form_view = self.env.ref('advance_vehicle_repair.vehicle_booking_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Booking',
            'res_model': 'vehicle.booking',
            'view_mode': 'form',
            'views': [(form_view.id, 'form')],
            'res_id': booking.id,
            'target': 'current',
        }
