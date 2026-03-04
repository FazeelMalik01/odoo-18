# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleNationalAddress(WebsiteSale):
    """Extend address form to include and save national_address for Saudi addresses."""

    WRITABLE_PARTNER_FIELDS = WebsiteSale.WRITABLE_PARTNER_FIELDS + ['national_address']

    def _parse_form_data(self, form_data):
        """Ensure national_address is included in address values (it may be blacklisted by default)."""
        address_values, extra_form_data = super()._parse_form_data(form_data)
        ResPartner = request.env['res.partner']
        if 'national_address' in form_data and 'national_address' in ResPartner._fields:
            val = form_data.get('national_address')
            if isinstance(val, str):
                val = val.strip()
            address_values['national_address'] = ResPartner._fields['national_address'].convert_to_cache(
                val or False, ResPartner
            )
        return address_values, extra_form_data
