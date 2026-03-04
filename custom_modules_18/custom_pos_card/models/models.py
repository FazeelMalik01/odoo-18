# -*- coding: utf-8 -*-

from odoo import models, api


class PosPayment(models.Model):
    _inherit = "pos.payment"

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Override to include card_no field for POS frontend."""
        return [
            'id', 'name', 'pos_order_id', 'amount', 'payment_method_id',
            'payment_date', 'card_type', 'card_brand', 'card_no', 'cardholder_name',
            'transaction_id', 'payment_status', 'ticket', 'is_change', 'uuid'
        ]
