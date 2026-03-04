# -*- coding: utf-8 -*-

from odoo.tools import str2bool
from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        """ Ensure invoice is created for SMSA delivery orders when payment is done.

        The standard flow only creates invoices when sale.automatic_invoice is enabled.
        For SMSA orders, we temporarily enable automatic invoicing before calling super(),
        so that the invoice is created and posted in the same flow (including payment
        reconciliation).
        """
        ir_config = self.env['ir.config_parameter'].sudo()
        auto_invoice = str2bool(ir_config.get_param('sale.automatic_invoice'))
        smsa_done_tx = self.filtered(
            lambda tx: tx.state == 'done'
            and tx.sale_order_ids
            and any(so.carrier_id and so.carrier_id.delivery_type == 'smsa' for so in tx.sale_order_ids)
        )

        if smsa_done_tx and not auto_invoice:
            ir_config.set_param('sale.automatic_invoice', 'True')

        try:
            return super()._post_process()
        finally:
            if smsa_done_tx and not auto_invoice:
                ir_config.set_param('sale.automatic_invoice', str(auto_invoice))
