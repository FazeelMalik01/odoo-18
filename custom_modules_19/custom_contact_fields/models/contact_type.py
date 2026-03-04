from odoo import models, fields


class ContactType(models.Model):
    _name = 'contact.type'
    _description = 'Contact Type'
    _order = 'sequence, name'

    name = fields.Char(string='Contact Type', required=True, translate=True)
    code = fields.Char(string='Code', required=True, help='Technical code used for field visibility logic')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'The code must be unique!'),
    ]
