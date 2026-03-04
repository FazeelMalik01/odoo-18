from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _send_payment_succeeded_for_order_mail(self):
        for order in self:
            if order.state in ['draft', 'sent']:
                order.action_confirm()

        return super()._send_payment_succeeded_for_order_mail()