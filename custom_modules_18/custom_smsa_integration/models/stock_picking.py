# -*- coding: utf-8 -*-

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    carrier_waybill_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Waybill PDF",
        copy=False,
        help="PDF waybill from carrier (e.g. SMSA AWB)",
    )

    def action_download_waybill(self):
        """Open waybill PDF in new tab for download."""
        self.ensure_one()
        if self.carrier_waybill_attachment_id:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self.carrier_waybill_attachment_id.id}?download=true',
                'target': 'new',
            }
        return False
