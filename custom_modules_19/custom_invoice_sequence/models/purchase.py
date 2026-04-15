import base64
import os
import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        this_file = os.path.abspath(__file__)
        module_dir = os.path.dirname(os.path.dirname(this_file))

        company_id = self.env.company.id

        if company_id == 1:
            terms_filename = 'aterms.jpeg'
            stamp_filename = 'astamp.png'
        elif company_id == 2:
            terms_filename = 'gterms.jpeg'
            stamp_filename = 'gstamp.jpeg'
        else:
            _logger.warning("=== NO IMAGE CONFIG for company_id: %s", company_id)
            return res

        terms_path = os.path.join(module_dir, 'static', 'src', 'img', terms_filename)
        stamp_path = os.path.join(module_dir, 'static', 'src', 'img', stamp_filename)

        _logger.warning("=== COMPANY: %s | TERMS: %s | EXISTS: %s", company_id, terms_path, os.path.exists(terms_path))
        _logger.warning("=== COMPANY: %s | STAMP: %s | EXISTS: %s", company_id, stamp_path, os.path.exists(stamp_path))

        html_parts = []

        if os.path.exists(terms_path):
            with open(terms_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            html_parts.append(
                f'<p><img src="data:image/jpeg;base64,{b64}" style="max-width:100%;display:block;"/></p>'
            )

        if os.path.exists(stamp_path):
            with open(stamp_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            html_parts.append(
                f'<p><img src="data:image/png;base64,{b64}" style="max-width:100%;display:block;"/></p>'
            )

        if html_parts:
            res['note'] = ''.join(html_parts)

        return res