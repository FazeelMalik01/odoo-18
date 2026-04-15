from datetime import timedelta

from odoo import api, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.onchange('use_date')
    def _onchange_use_date_recompute_related_dates(self):
        """When Best Before is edited, auto-shift the other lot dates.

        In product_expiry, dates are primarily derived from expiration_date.
        This onchange lets users drive the timeline from use_date (Best Before)
        using product tenure values configured on the product template.
        """
        for lot in self:
            if not lot.use_date or not lot.product_id or not lot.product_id.use_expiration_date:
                continue

            product_tmpl = lot.product_id.product_tmpl_id
            expiration_date = lot.use_date + timedelta(days=product_tmpl.use_time or 0)

            lot.expiration_date = expiration_date
            lot.removal_date = expiration_date - timedelta(days=product_tmpl.removal_time or 0)
            lot.alert_date = expiration_date - timedelta(days=product_tmpl.alert_time or 0)
