# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    social_security_no = fields.Char(
        string='Social Security No',
        help='Social Security Number in format XXX.XXXX.XXXX.XX'
    )
    
    partner_zip_code = fields.Char(
        string='Partner Zip Code',
        help='Additional zip code field for partners'
    )
    
    availability_weekdays = fields.Char(
        string='Availability',
        help='Comma-separated list of weekdays when partner is available (e.g., "monday,tuesday,wednesday")'
    )
    
    middle_name = fields.Char(
        string='Middle Name',
        help='Middle name of the partner'
    )
    
    last_name = fields.Char(
        string='Last Name',
        help='Last name of the partner'
    )
    
    title_selection = fields.Selection(
        [
            ('sir', 'Sir'),
            ('madam', 'Madam'),
        ],
        string='Title',
        help='Title of the partner'
    )
    
    mobile = fields.Char(
        string='Mobile',
        help='Mobile phone number'
    )
    
    city_1 = fields.Char(
        string='City',
        help='City selected from zip code'
    )
    
    @api.model
    def create(self, vals):
        """Override create to sync city_1 to city"""
        if 'city_1' in vals and vals.get('city_1'):
            vals['city'] = vals['city_1']
        return super(ResPartner, self).create(vals)
    
    def write(self, vals):
        """Override write to sync city_1 to city"""
        # If city_1 is being updated, also update city with the same value
        if 'city_1' in vals and vals.get('city_1'):
            vals['city'] = vals['city_1']
        return super(ResPartner, self).write(vals)

    @api.model
    def _get_frontend_writable_fields(self):
        """Override to add social_security_no and partner_zip_code to frontend writable fields"""
        fields = super()._get_frontend_writable_fields()
        fields.add('social_security_no')
        fields.add('partner_zip_code')
        fields.add('availability_weekdays')
        fields.add('middle_name')
        fields.add('last_name')
        fields.add('title_selection')
        fields.add('city_1')
        fields.add('mobile')
        return fields
 
    @api.model
    def create(self, vals):
        # Safely build full name before creation
        if any(k in vals for k in ('name', 'middle_name', 'last_name')):
            first = str(vals.get('name') or '').strip()
            middle = str(vals.get('middle_name') or '').strip()
            last = str(vals.get('last_name') or '').strip()

            parts = [p for p in [first, middle, last] if p]
            full_name = ' '.join(parts)
            if full_name:
                vals['name'] = full_name

        return super().create(vals)

    def write(self, vals):
        # Only rebuild name if name / middle / last provided
        if any(k in vals for k in ('name', 'middle_name', 'last_name')):
            for partner in self:
                first = str(vals.get('name', partner.name) or '').strip()
                middle = str(vals.get('middle_name', partner.middle_name) or '').strip()
                last = str(vals.get('last_name', partner.last_name) or '').strip()

                parts = [p for p in [first, middle, last] if p]
                full_name = ' '.join(parts)

                if full_name:
                    vals['name'] = full_name

        return super().write(vals)