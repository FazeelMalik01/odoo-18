from odoo import models, fields, api

class VehicleFluids(models.Model):
    _name = 'vehicle.fluids'
    _description = 'Vehicle Fluids'

    name = fields.Char(string="Name", required=True)
    component_side = fields.Selection([
            ('front', 'Front'),
            ('rear', 'Rear'),
            ('top', 'Top'),
            ('center', 'Center'),
            ('bottom', 'Bottom'),
            ('front_left', 'Front Left'),
            ('front_right', 'Front Right'),
            ('rear_left', 'Rear Left'),
            ('rear_right', 'Rear Right'),
        ], string="Vehicle Side", required=True)