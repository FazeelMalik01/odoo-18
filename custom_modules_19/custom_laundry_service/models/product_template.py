# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_size = fields.Selection([
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
        ('small_ironing', 'Small Ironing'),
        ('medium_ironing', 'Medium Ironing'),
        ('large_ironing', 'Large Ironing')
    ], string='Service Size', tracking=True)

    _sql_constraints = [
        ('unique_service_size', 'UNIQUE(service_size)', 
         'Only one product can have each service size value (Small, Medium, Large, Small Ironing, Medium Ironing, or Large Ironing). Please delete the existing product with this service size first.')
    ]

    @api.constrains('service_size')
    def _check_unique_service_size(self):
        """Ensure only one product can have each service_size value"""
        for record in self:
            if record.service_size:
                # Find other products with the same service_size
                duplicate = self.env['product.template'].search([
                    ('service_size', '=', record.service_size),
                    ('id', '!=', record.id)
                ], limit=1)
                
                if duplicate:
                    size_label = dict(record._fields['service_size'].selection).get(record.service_size, record.service_size)
                    raise ValidationError(
                        f'Only one product can have the "{size_label}" service size. '
                        f'Product "{duplicate.name}" (ID: {duplicate.id}) already has this service size. '
                        f'Please delete or change the service size of the existing product first.'
                    )

