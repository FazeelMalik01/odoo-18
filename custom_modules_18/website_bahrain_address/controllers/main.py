import logging
from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class WebsiteSaleBahrain(WebsiteSale):

    def _get_mandatory_address_fields(self, country_sudo):
        field_names = super()._get_mandatory_address_fields(country_sudo)

        if country_sudo and country_sudo.code == 'BH':
            field_names.discard('street')
            field_names.discard('street2')
            field_names.discard('zip')
            field_names.discard('city')
            field_names |= {'bahrain_building', 'bahrain_road', 'bahrain_block'}

        _logger.info("Mandatory fields for %s: %s",
                     country_sudo and country_sudo.code, field_names)
        return field_names

    def _parse_form_data(self, form_data):
        address_values, extra_form_data = super()._parse_form_data(form_data)

        # ── Mobile ───────────────────────────────────────────────────────────
        # `mobile` is not in Odoo's default address fields whitelist so the
        # base _parse_form_data lands it in extra_form_data.  Move it into
        # address_values so it is written to res.partner.
        if 'mobile' in extra_form_data:
            address_values['mobile'] = extra_form_data.pop('mobile') or False

        # ── Bahrain custom fields ─────────────────────────────────────────────
        for field in ('bahrain_flat', 'bahrain_building', 'bahrain_road', 'bahrain_block'):
            if field in extra_form_data:
                address_values[field] = extra_form_data.pop(field) or False

        # ── Synthesise street for Bahrain ─────────────────────────────────────
        # Keeps partner.street readable for PDF reports / delivery labels and
        # prevents any residual "street is required" check in the base controller.
        country_id = address_values.get('country_id')
        if country_id:
            country = http.request.env['res.country'].sudo().browse(country_id)
            if country.code == 'BH':
                parts = list(filter(None, [
                    address_values.get('bahrain_flat'),
                    address_values.get('bahrain_building'),
                    address_values.get('bahrain_road'),
                    address_values.get('bahrain_block'),
                ]))
                address_values['street'] = ', '.join(parts) or '—'
                _logger.info("Synthesised street for BH: %s", address_values['street'])

        return address_values, extra_form_data