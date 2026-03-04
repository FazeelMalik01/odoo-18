from odoo import models, fields

class VehicleItemCategory(models.Model):
    _name = 'vehicle.item.category'
    _description = 'Vehicle Item Category'

    name = fields.Char(string='Category Name', required=True)

