from odoo import fields, models, api

class VehicleItems(models.Model):
    _name = 'vehicle.items'
    _description = "Vehicle Items"

    name = fields.Char(string="Name", required=True)
    vehicle_category_id = fields.Many2one('vehicle.item.category', string=' Item Category', required=True)



