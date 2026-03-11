from odoo import fields, models, api

class VehicleServices(models.Model):
    _name = 'vehicle.services'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Vehicle Services"

    name = fields.Char(string="Name", required=True, tracking=True)
    product_id = fields.Many2one('product.product',string='Product')
    service_team_id=fields.Many2one('vehicle.teams', string="Service Team")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True, tracking=True)
    service_amount = fields.Float(string="Service Charge", required=True, tracking=True)
    colr_picker = fields.Integer(string="color", tracking=True)
    is_recurring = fields.Boolean(string="Recurring", tracking=True)
    recurring_days = fields.Integer(string="Days After", help="Number of days after which service repeats")
    estimated_time = fields.Float( string="Estimated Time", help="Estimated service duration")