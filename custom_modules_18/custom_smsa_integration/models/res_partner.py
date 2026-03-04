# -*- coding: utf-8 -*-

import re
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    national_address = fields.Char(
        string="National Address",
        size=8,
        help="Saudi National Address (Short Address): 4 letters + 4 numbers, e.g. RRRD2929 (Region, Branch, Division, Building)",
    )

    @api.constrains('national_address')
    def _check_national_address_format(self):
        """Validate format: 4 uppercase letters + 4 digits."""
        for partner in self:
            if not partner.national_address:
                continue
            val = partner.national_address.strip().upper()
            if not re.match(r'^[A-Z]{4}[0-9]{4}$', val):
                raise models.ValidationError(_(
                    "National Address must be 4 letters followed by 4 numbers (e.g. RRRD2929)"
                ))
