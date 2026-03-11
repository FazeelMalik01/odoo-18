from odoo import fields, models, api

class VehicleSpareParts(models.Model):
    _inherit = 'product.product'

    spare_part = fields.Boolean(string="Vehicle Spare part")
    part_condition = fields.Selection([
    ('new', 'New'),
    ('used', 'Used'),
    ('commercial', 'Commercial')
    ], string="Part Condition")
    linked_service_id = fields.Many2one('vehicle.services', string="Linked Auto-Service")
    vehicle_compatibility_ids = fields.One2many( 'product.vehicle.compatibility', 'product_id', string="Vehicle Compatibility Matrix")

class VehicleSparePart(models.Model):
    _inherit = 'product.template'

    spare_part = fields.Boolean(string="Vehicle Spare part")
