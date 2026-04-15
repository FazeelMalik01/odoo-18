# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    section_field = fields.Many2one('rental.section', string='Section', ondelete='set null')
