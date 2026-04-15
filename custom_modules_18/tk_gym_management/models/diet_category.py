from odoo import fields, models


class DietCategory(models.Model):
    """diet category"""
    _name = 'diet.category'
    _description = __doc__

    name = fields.Char(string='Diet Category')


class DietType(models.Model):
    """Diet Types"""
    _name = 'diet.type'
    _description = __doc__

    name = fields.Char(string='Diet Type')
