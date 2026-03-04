from odoo import models, fields

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    no_of_workers = fields.Integer(string="No of Workers", default=1)

