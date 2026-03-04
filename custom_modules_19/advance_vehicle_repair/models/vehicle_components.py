from odoo import models, fields, api

class VehicleComponents(models.Model):
    _name = 'vehicle.components'
    _description = 'Vehicle Components'

    name = fields.Char(string="Name", required=True)
    side = fields.Selection([
        ('front', 'Front'),
        ('rear', 'Rear'),
        ('left', 'Left'),
        ('right', 'Right'),
        ('center', 'Center'),
        ('top', 'Top'),
        ('bottom', 'Bottom'),
        ('front_left', 'Front Left'),
        ('front_right', 'Front Right'),
        ('rear_left', 'Rear Left'),
        ('rear_right', 'Rear Right'),
        ('upper_left', 'Upper Left'),
        ('upper_right', 'Upper Right'),
        ('lower_left', 'Lower Left'),
        ('lower_right', 'Lower Right'),
        ], string="Vehicle Side", required=True)
