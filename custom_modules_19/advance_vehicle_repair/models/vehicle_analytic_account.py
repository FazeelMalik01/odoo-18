from odoo import models, fields, api

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    repair_line_id = fields.Many2one(
        'vehicle.repair.services.line',
        string="Repair Task"
    )