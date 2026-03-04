from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResCompany(models.Model):
    _inherit = 'res.company'

    show_coach = fields.Boolean(string="Show Coach?", default=True)
    show_team = fields.Boolean(string="Show Team?", default=True)
    loaylty_pointer_per_purchase_amount = fields.Float(string="Loyalty point per JOD", store=True)
    minimum_points_required = fields.Integer(string="Minimum Loyalty Points Required for Discount", help="User must have at least this number of points to apply a loyalty discount.")
    discount_value = fields.Integer(string="Discount", store=True)
    commission_cycle_days = fields.Integer(string="Commission Cycle (days)", default=90)
    test_today = fields.Date("Test Today", help="Optional date to override today for testing")