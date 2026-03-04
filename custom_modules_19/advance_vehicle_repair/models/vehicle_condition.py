from odoo import fields, models, api

class VehicleCondition(models.Model):
    _name = 'vehicle.condition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Vehicle Conditions"
    _rec_name = 'name'

    name = fields.Char(string="Condition", required=True, tracking=True)
    short_code = fields.Char(string="Short Code", required=True, tracking=True)