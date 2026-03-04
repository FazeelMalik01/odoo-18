from odoo import fields, models, api

class VehicleSpareParts(models.Model):
    _inherit = 'product.product'

    spare_part = fields.Boolean(string="Vehicle Spare part")

class VehicleSparePart(models.Model):
    _inherit = 'product.template'

    spare_part = fields.Boolean(string="Vehicle Spare part")