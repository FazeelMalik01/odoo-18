from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class VehicleRegister(models.Model):
    _name = 'vehicle.register'
    _description = "Vehicle Register"
    _rec_name = 'registration_no'

    sequence = fields.Char(string="Sequence No", required=True, copy=False, index=True, readonly=True, default=lambda self: _('New'))
    registration_no = fields.Char(string="Registration No", translate=True, required=True)
    vin_no = fields.Char(string="VIN Number", translate=True, required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    brand_id = fields.Many2one('vehicle.brand', string="Brand")
    model_id = fields.Many2one('vehicle.model', string="Model", domain="[('brand_id', '=', brand_id)]")
    fuel_type_id = fields.Many2one('vehicle.fuel.type', string="Fuel Type")
    transmission_type = fields.Selection([
        ('manual', "Manual"),
        ('automatic', "Automatic"),
        ('cvt', "CVT")
        ], string="Transmission Type")
    state = fields.Selection([
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ],
        string='State', required=True, default='active',
    )
    phone = fields.Char(
    related='customer_id.phone',
    store=True,
    index=True
    )
    color = fields.Char(string='Color')
    kilometer = fields.Float(string='Current Kilometer')
    model_year = fields.Many2one('vehicle.model.year', string="Model Year")
    kilometer_log_ids = fields.One2many(
    'vehicle.kilometer.log',
    'vehicle_id',
    string="Kilometer History"
    )

    def action_activate(self):
        self.write({
            'state' : 'active'
        })

    def action_cancel(self):
        self.write({
            'state' : 'canceled'
        })

    @api.constrains('registration_no')
    def _check_registration_no(self):
        for record in self:
            existing = self.sudo().search([('registration_no', '=', record.registration_no), ('id', '!=', record.id)])
            if existing:
                raise ValidationError(_("The registration number '%s' already exists for another vehicle.") % record.registration_no)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence', _('New')) == _('New'):
                vals['sequence'] = self.env['ir.sequence'].next_by_code('vehicle.register') or _('New')
        record = super(VehicleRegister, self).create(vals_list)
        return record

    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []

        if name:
            domain = [
                '|', '|', '|',
                ('registration_no', operator, name),
                ('vin_no', operator, name),
                ('customer_id.name', operator, name),
                ('phone', operator, name),
            ]
            args = domain + args

        records = self.search(args, limit=limit)
        return [(rec.id, rec.display_name) for rec in records]

    def write(self, vals):
        if 'kilometer' in vals:
            for record in self:
                old_km = record.kilometer
                new_km = vals.get('kilometer')

                if new_km and new_km != old_km:
                    self.env['vehicle.kilometer.log'].create({
                        'vehicle_id': record.id,
                        'kilometer': new_km,
                    })

        return super(VehicleRegister, self).write(vals)
    
    def create_vehicle_booking(self):
        self.ensure_one()

        booking = self.env['vehicle.booking'].create({
            'customer_id': self.customer_id.id,
            'vehicle_source': 'register',
            'vehicle_register_id': self.id,
            'brand_id': self.brand_id.id,
            'model_id': self.model_id.id,
            'fuel_type_id': self.fuel_type_id.id,
            'registration_no': self.registration_no,
            'vin_no': self.vin_no,
            'transmission_type': self.transmission_type,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Booking',
            'res_model': 'vehicle.booking',
            'view_mode': 'form',
            'res_id': booking.id,
            'target': 'current',
        }

    def create_job_card(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Select Booking Type',
            'res_model': 'jobcard.booking.type.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_customer_id': self.customer_id.id,
                'default_vehicle_register_id': self.id,
            }
        }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # This contains what user typed before clicking Create
        if self.env.context.get('default_name') and not res.get('registration_no'):
            res['registration_no'] = self.env.context.get('default_name')

        return res
