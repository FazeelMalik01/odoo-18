# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    bahrain_flat = fields.Char(
        string='Flat',
        help='Flat number (Optional for Bahrain addresses)'
    )
    bahrain_building = fields.Char(
        string='Building',
        help='Building name or number (Mandatory for Bahrain addresses)'
    )
    bahrain_road = fields.Char(
        string='Road',
        help='Road name or number (Mandatory for Bahrain addresses)'
    )
    bahrain_block = fields.Char(
        string='Block',
        help='Block number (Mandatory for Bahrain addresses)'
    )
