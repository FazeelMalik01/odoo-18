from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    webflow_collection_id = fields.Char("Webflow Collection ID", readonly=True)
    webflow_locale_id     = fields.Char("Webflow Locale ID",     readonly=True)
    webflow_location_id   = fields.Char("Webflow Location ID",   readonly=True)
    webflow_zips          = fields.Char("Zips Supported")