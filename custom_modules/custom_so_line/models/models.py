# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    serial = fields.Many2one(
        "stock.lot",
        string="Serial",
        domain="[('product_id', '=', product_id)]",
    )

    @api.onchange("product_id")
    def _onchange_product_id_tracking(self):
        """When product changes:
        - If tracking is 'lot', propose lots for this product
        - Otherwise clear the selected serial
        """
        domain = []
        if self.product_id and self.product_id.tracking == "lot":
            domain = [('product_id', '=', self.product_id.id)]
        else:
            self.serial = False
        return {"domain": {"serial": domain}}

    @api.onchange("serial")
    def _onchange_serial_set_price(self):
        """If product is lot-tracked and a serial is selected, set price from serial.my_price."""
        if not self.serial or not self.product_id:
            return
        # Only apply for lot-tracked products and matching product on the lot
        if self.product_id.tracking == "lot" and (not self.serial.product_id or self.serial.product_id == self.product_id):
            # Assume custom field my_price exists on stock.lot
            self.price_unit = self.serial.my_price or 0.0