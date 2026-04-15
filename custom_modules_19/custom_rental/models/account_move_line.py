from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_tip = fields.Boolean(string="Is Tip", default=False)