from odoo import fields, models, api

class VehicleModel(models.Model):
    _name = 'vehicle.model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Vehicle Models"

    name = fields.Char(string="Name", required=True, tracking=True)
    brand_id = fields.Many2one('vehicle.brand', string="Vehicle Brand")

