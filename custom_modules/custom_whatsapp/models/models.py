from odoo import models, fields, api
import phonenumbers  # external library for country codes

class ResPartner(models.Model):
    _inherit = 'res.partner'

    country_dial_code = fields.Selection(
        selection=lambda self: self._get_country_code_selection(),
        string='Country Dial Code'
    )

    @api.model
    def _get_country_code_selection(self):
        """Generate selection list of all country calling codes."""
        from phonenumbers.data import _COUNTRY_CODE_TO_REGION_CODE
        codes = []
        seen = set()
        for code, regions in _COUNTRY_CODE_TO_REGION_CODE.items():
            if code not in seen:
                seen.add(code)
                # Take the first country as label
                country = regions[0] if regions else ''
                label = f"+{code} ({country})"
                codes.append((f"+{code}", label))
        # Sort nicely by code
        return sorted(codes, key=lambda x: int(x[0].replace('+', '')))
