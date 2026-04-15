from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    cc_number = fields.Char(string="Card Number")
    cc_exp_month = fields.Char(string="Expiry Month")
    cc_exp_year = fields.Char(string="Expiry Year")
    cc_cvv = fields.Char(string="CVV")
