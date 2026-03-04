from odoo import fields, models, api

class VehicleLocation(models.Model):
    _name = 'vehicle.location'
    _description = "Vehicle Parts"

    name=fields.Char(string="Location", required=True)