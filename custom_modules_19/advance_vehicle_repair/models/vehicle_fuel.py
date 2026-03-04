from odoo import fields, models, api

class VehicleFuel(models.Model):
    _name = 'vehicle.fuel.type'
    _description = "Vehicle Fuel Types"

    name = fields.Char(string="Name", required=True)

