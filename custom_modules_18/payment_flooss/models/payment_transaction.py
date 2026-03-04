# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_flooss.const import PAYMENT_STATUS_MAPPING

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    flooss_type = fields.Char(string="Flooss Transaction Type")
    flooss_reference_id = fields.Char(string="Flooss Reference ID ")
    flooss_created_at = fields.Char(string="Flooss Created At")
    flooss_transaction_id = fields.Char(string="Flooss Created At")
    flooss_payment_status = fields.Char(string="Flooss Status")
    flooss_webhook_payload = fields.Text(string="Flooss Webhook Payload")

    def _get_specific_processing_values(self, processing_values):
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'flooss':
            return res

        # Only send order if OTP is verified
        phone = self.flooss_verified_phone
        if not phone:
            _logger.info("Flooss: OTP not verified yet, skipping order creation for transaction %s", self.reference)
            return res

        payload = self._flooss_prepare_order_payload(tx_sudo=self, phone=phone)
        _logger.info("Sending Flooss '/checkout/orders' request for transaction %s:\n%s",
                     self.reference, pprint.pformat(payload))

        idempotency_key = payment_utils.generate_idempotency_key(self, scope='payment_request_order')
        order_data = self.provider_id._flooss_make_request(
            '/pie/api/v1/bo/merchants/payment-request',
            json_payload=payload,
            idempotency_key=idempotency_key
        )

        _logger.info("Response of Flooss '/checkout/orders' request for transaction %s:\n%s",
                     self.reference, pprint.pformat(order_data))

        order_id = None
        if isinstance(order_data, dict):
            order_id = (order_data.get('data') or {}).get('id') or order_data.get('id')
        if not order_id:
            raise ValidationError(
                _("Flooss: could not find order id in payment response: %s") % pprint.pformat(order_data))

        return {'order_id': order_id}

    def _flooss_prepare_order_payload(self, tx_sudo=None, phone=None):
        tx_sudo = tx_sudo or self
        phone = phone or getattr(tx_sudo, 'flooss_verified_phone', None)
        if not tx_sudo or not phone:
            _logger.info("Flooss: OTP not verified yet, skipping order creation for transaction %s", tx_sudo.reference)
            return {}
        return {
            "merchantId": self.provider_id.flooss_merchant_id,
            "transactionAmount": float(tx_sudo.amount),
            "phoneNumber": phone,
            "merchantTransactionType": "ONLINE_CHECKOUT",
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'flooss' or len(tx) == 1:
            return tx

        # multiple transactions with the same reference_id? fallback to id
        filtered = self.env['payment.transaction'].search([
            ('reference', '=', notification_data.get('reference_id')),
            ('id', '=', notification_data.get('id'))
        ])
        return filtered

    def _handle_notification_data(self, provider_code, data):
        if provider_code != 'flooss':
            return super()._handle_notification_data(provider_code, data)

        status = data.get('status')
        if status in PAYMENT_STATUS_MAPPING:
            self.write({
                'state': PAYMENT_STATUS_MAPPING[status],
                'acquirer_reference': data.get('reference_id'),
                'flooss_type': data.get('merchantTransactionType', False),
            })
        else:
            _logger.warning("Flooss payment notification with unknown status: %s", status)

        return True

    def action_online_checkout(self):
        for record in self:
            if record.provider_id.code != 'flooss':
                raise ValidationError(_("This record is not a Flooss Payment"))

            payload = record.flooss_webhook_payload
            if not payload:
                message = "No webhook data received yet from Flooss."
                notif_type = "warning"
            else:
                import ast
                try:
                    data = ast.literal_eval(payload)
                    status = str(data.get("status", "Unknown")).strip().upper()
                    tx_number = data.get("transactionNumber", "N/A")

                    if status == "SUCCESS":
                        message = f"Payment Successful for Transaction Number {tx_number}"
                        notif_type = "success"
                    else:
                        message = "Payment Failed"
                        notif_type = "danger"

                except Exception:
                    message = "Webhook received, but could not parse payload."
                    notif_type = "danger"

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Flooss Payment Notification',
                    'message': message,
                    'type': notif_type,
                    'sticky': False,
                }
            }
