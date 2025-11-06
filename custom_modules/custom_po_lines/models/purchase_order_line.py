# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    barcode = fields.Char(
        string='Barcode',
        help='Product barcode for scanning',
        copy=False
    )

    @api.onchange('product_id')
    def _onchange_product_id_barcode(self):
        """Set barcode from product when product is selected"""
        if self.product_id and self.product_id.barcode:
            self.barcode = self.product_id.barcode

    @api.onchange('barcode')
    def _onchange_barcode(self):
        """Find product by barcode when barcode is scanned"""
        if self.barcode and not self.product_id:
            product = self.env['product.product'].search([
                ('barcode', '=', self.barcode),
                ('purchase_ok', '=', True)
            ], limit=1)
            if product:
                self.product_id = product
                self._product_id_change()
                self._suggest_quantity()
