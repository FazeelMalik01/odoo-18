# -*- coding: utf-8 -*-
from odoo import models, fields, api


class QualityCheckImage(models.Model):
    _name = 'quality.check.image'
    _description = 'Quality Check Image'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=False)
    image = fields.Binary(string='Image', required=True, attachment=True)
    sequence = fields.Integer(string='Sequence', default=10)
    quality_check_id = fields.Many2one(
        'quality.check',
        string='Quality Check',
        required=True,
        ondelete='cascade',
        index=True
    )

