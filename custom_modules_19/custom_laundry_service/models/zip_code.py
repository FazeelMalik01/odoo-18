from odoo import models, fields

class City(models.Model):
    _name = 'laundry.city'
    _description = 'City'
    _rec_name = 'name'

    name = fields.Char(string='City Name', required=True)

class ZipCode(models.Model):
    _name = 'laundry.zip.code'
    _description = 'Zip Code'

    name = fields.Char(string='Zip Code', required=True)
    line_ids = fields.One2many(
        'laundry.zip.code.line',
        'zip_id',
        string='Details'
    )
    partner_zip_code_ids = fields.One2many(
        'laundry.partner.zip.code',
        'zip_code_id',
        string='Partner Zip Codes'
    )


class ZipCodeLine(models.Model):
    _name = 'laundry.zip.code.line'
    _description = 'Zip Code Line'
    _rec_name = 'description'

    zip_id = fields.Many2one(
        'laundry.zip.code',
        string='Zip Code',
        ondelete='cascade'
    )
    description = fields.Char(string='Zip Codes')
    city_ids = fields.Many2many(
        'laundry.city',
        'zip_code_line_city_rel',
        'zip_code_line_id',
        'city_id',
        string='Cities',
        help='Cities associated with this zip code'
    )


class PartnerZipCode(models.Model):
    _name = 'laundry.partner.zip.code'
    _description = 'Partner Zip Code Assignment'
    _rec_name = 'user_id'

    zip_code_id = fields.Many2one(
        'laundry.zip.code',
        string='Zip Code Configuration',
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        help='Select the user/partner to assign zip codes'
    )
    zip_code_line_ids = fields.Many2many(
        'laundry.zip.code.line',
        'partner_zip_code_line_rel',
        'partner_zip_code_id',
        'zip_code_line_id',
        string='Zip Codes',
        help='Select multiple zip codes to assign to this user'
    )
