# -*- coding: utf-8 -*-

from odoo import models, fields


class RentalSection(models.Model):
    _name = 'rental.section'
    _description = 'Rental Section'
    _order = 'name asc'

    name = fields.Char(string='Section', required=True)
