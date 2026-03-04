from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

class ResPartner(models.Model):
    _inherit = 'res.partner'

    vehicle_register_ids = fields.One2many(
        'vehicle.register',
        'customer_id',
        string='Registered Vehicles'
    )
    @api.constrains('phone')
    def _check_unique_phone(self):
        for record in self:
            if record.phone:
                existing = self.search([
                    ('phone', '=', record.phone),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise ValidationError(
                        _("This phone number is already assigned to another customer: %s") 
                        % existing.name
                    )
    
    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        domain = domain or []

        if name:
            search_domain = [
                '|',
                ('name', operator, name),
                ('phone', operator, name),
            ]
            domain = search_domain + domain

        records = self.search(domain, limit=limit)
        return [(rec.id, rec.display_name) for rec in records]