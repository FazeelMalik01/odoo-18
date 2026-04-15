from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    po_number = fields.Char(string="PO Number", copy=False)
    order_id = fields.Char(string="Order ID", copy=False)
    amount_untaxed = fields.Monetary(string="Subtotal")

    @api.onchange('po_number')
    def _onchange_po_number_sync_sale(self):
        """If PO number edited on invoice, update linked sale order"""
        for move in self:
            if move.po_number and move.invoice_origin:
                sale = self.env['sale.order'].search(
                    [('name', '=', move.invoice_origin)],
                    limit=1
                )
                if sale:
                    sale.po_number = move.po_number