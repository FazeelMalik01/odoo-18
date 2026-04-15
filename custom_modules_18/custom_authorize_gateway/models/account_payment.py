from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_transaction_ids = fields.One2many(
        'payment.transaction', 'payment_id', string="Transactions"
    )

    is_authorize_payment = fields.Boolean(
        string="Authorize.Net Payment",
        compute="_compute_is_authorize_payment",
        store=True,
    )

    @api.depends('payment_transaction_ids.provider_id')
    def _compute_is_authorize_payment(self):
        for payment in self:
            payment.is_authorize_payment = any(
                tx.provider_id.code == 'authorize'
                for tx in payment.payment_transaction_ids
            )