# -*- coding: utf-8 -*-

from odoo import models, fields


class RentalZipcode(models.Model):
    _name = 'rental.zipcode'
    _description = 'Rental Zip Code'
    _check_company_auto = True

    name = fields.Char(string='Zip/Postal Code', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
    )
    city = fields.Char(string='City')
    state_id = fields.Many2one(
        'res.country.state',
        string='State',
        ondelete='restrict',
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
