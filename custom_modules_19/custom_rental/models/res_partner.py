from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    phone_secondary = fields.Char(string='Secondary Phone')
    last_name = fields.Char(string='Last Name')
