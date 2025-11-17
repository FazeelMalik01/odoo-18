# -*- coding: utf-8 -*-

import logging
import pprint

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def _safe_log_data(data):
    """ Safely convert data to string for logging, handling Unicode characters.
    
    :param data: The data to convert (dict, list, or any object)
    :return: ASCII-safe string representation
    """
    def _sanitize_value(value):
        """ Recursively sanitize values to be ASCII-safe. """
        if isinstance(value, (int, float, bool, type(None))):
            return value
        elif isinstance(value, str):
            # Replace non-ASCII characters with their Unicode escape sequences
            try:
                return value.encode('ascii', 'replace').decode('ascii')
            except (UnicodeEncodeError, UnicodeDecodeError):
                # If that fails, use a more aggressive approach
                return value.encode('unicode_escape').decode('ascii', 'replace')
        elif isinstance(value, dict):
            return {k: _sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return type(value)(_sanitize_value(item) for item in value)
        else:
            return str(value).encode('ascii', 'replace').decode('ascii')
    
    try:
        sanitized = _sanitize_value(data)
        return pprint.pformat(sanitized)
    except Exception:
        # Ultimate fallback
        return str(data).encode('ascii', 'replace').decode('ascii')


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    eazypay_global_transaction_id = fields.Char(
        string="EazyPay Global Transaction ID",
        help="The global transaction ID returned by EazyPay",
        readonly=True,
    )

    def _get_specific_processing_values(self, processing_values):
        """ Override of `payment` to return EazyPay-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'eazypay':
            return res

        # Set operation to online_redirect for redirect flow
        if not self.operation:
            self.operation = 'online_redirect'
        
        # Create invoice in EazyPay
        invoice_data = self._eazypay_create_invoice()
        
        if not invoice_data.get('data') or not invoice_data['data']:
            error_msg = invoice_data.get('result', {}).get('description', 'Unknown error')
            raise ValidationError(_("EazyPay: %s", error_msg))
        
        payment_info = invoice_data['data'][0]
        payment_url = payment_info.get('paymentUrl')
        global_transaction_id = payment_info.get('globalTransactionsId')
        
        # Store the global transaction ID
        self.write({
            'eazypay_global_transaction_id': global_transaction_id,
            'provider_reference': global_transaction_id,
        })
        
        return {
            'payment_url': payment_url,
            'global_transaction_id': global_transaction_id,
        }

    def _eazypay_create_invoice(self):
        """ Create an invoice in EazyPay and return the payment URL.

        :return: The invoice creation response.
        :rtype: dict
        """
        # Get base URL for return and webhook URLs
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        # Format amount to string with 3 decimal places
        amount_str = f"{self.amount:.3f}"
        
        # Get partner phone and country code
        partner_phone = self.partner_phone or ''
        country_code = ''
        mobile = ''
        
        if partner_phone:
            # Extract country code if present (e.g., +973 or 973)
            phone_clean = partner_phone.replace('+', '').replace(' ', '').replace('-', '')
            # Try to extract country code (assuming first 1-3 digits)
            # This is a simple extraction - you may need to adjust based on your needs
            if phone_clean and phone_clean[0].isdigit():
                # Common country codes are 1-3 digits
                for i in range(1, min(4, len(phone_clean) + 1)):
                    potential_code = phone_clean[:i]
                    if potential_code.isdigit():
                        country_code = potential_code
                        mobile = phone_clean[i:] if len(phone_clean) > i else ''
                        break
        
        # If no country code extracted, use default or partner country
        if not country_code and self.partner_country_id:
            # Map common country codes - you may need to expand this
            country_code_map = {
                'BH': '973',  # Bahrain
                'SA': '966',  # Saudi Arabia
                'AE': '971',  # UAE
                'KW': '965',  # Kuwait
                'QA': '974',  # Qatar
                'OM': '968',  # Oman
            }
            country_code = country_code_map.get(self.partner_country_id.code, '973')
            mobile = phone_clean if phone_clean else ''
        
        # If still no country code, use default
        if not country_code:
            country_code = '973'  # Default to Bahrain
            mobile = phone_clean if phone_clean else ''
        
        # Prepare return URL - EazyPay expects format with EAZY_GLOBAL_TRN_ID placeholder
        # EazyPay will replace EAZY_GLOBAL_TRN_ID with the actual global transaction ID
        return_url = f"{base_url}/payment/eazypay/return/EAZY_GLOBAL_TRN_ID"
        webhook_url = f"{base_url}/payment/eazypay/webhook"
        
        payload = {
            'appId': self.provider_id.eazypay_app_id,
            'invoiceId': self.reference,
            'currency': self.currency_id.name,
            'amount': amount_str,
            'paymentMethod': self.provider_id.eazypay_payment_methods,
            'returnUrl': return_url,
            'firstName': self.partner_name.split()[0] if self.partner_name else '',
            'lastName': ' '.join(self.partner_name.split()[1:]) if self.partner_name and len(self.partner_name.split()) > 1 else (self.partner_name or ''),
            'customerEmail': self.partner_email or '',
            'customerCountryCode': country_code,
            'customerMobile': mobile or '00000000',
            'webhookUrl': webhook_url,
        }
        
        _logger.info(
            "Sending '/createInvoice' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat({**payload, 'appId': '***'})  # Hide app ID in logs
        )
        
        invoice_data = self.provider_id._eazypay_make_request('createInvoice', payload=payload)
        
        # Log response safely, handling Unicode characters
        _logger.info(
            "Response of '/createInvoice' request for transaction with reference %s:\n%s",
            self.reference, _safe_log_data(invoice_data)
        )
        
        return invoice_data

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return EazyPay-specific rendering values.

        :param dict processing_values: The processing values of the transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'eazypay':
            return res
        
        return {
            'payment_url': processing_values.get('payment_url'),
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on EazyPay notification data.

        :param str provider_code: The code of the provider handling the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction, if found.
        :rtype: recordset of `payment.transaction`
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'eazypay':
            return tx

        # Try to find transaction by global transaction ID
        global_transaction_id = notification_data.get('globalTransactionsId')
        if global_transaction_id:
            tx = self.search([
                ('provider_code', '=', 'eazypay'),
                ('eazypay_global_transaction_id', '=', global_transaction_id),
            ], limit=1)
        
        # Fallback to invoice ID
        if not tx:
            invoice_id = notification_data.get('invoiceId')
            if invoice_id:
                tx = self.search([
                    ('provider_code', '=', 'eazypay'),
                    ('reference', '=', invoice_id),
                ], limit=1)
        
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the notification data sent by EazyPay.

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'eazypay':
            return

        # Query payment status from EazyPay
        self._eazypay_query_payment_status()

    def _eazypay_query_payment_status(self):
        """ Query the payment status from EazyPay API.

        :return: None
        """
        if not self.eazypay_global_transaction_id:
            _logger.warning(
                "Cannot query payment status for transaction %s: missing global transaction ID",
                self.reference
            )
            return

        payload = {
            'appId': self.provider_id.eazypay_app_id,
            'globalTransactionsId': self.eazypay_global_transaction_id,
        }
        
        _logger.info(
            "Sending '/query' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat({**payload, 'appId': '***'})
        )
        
        try:
            query_data = self.provider_id._eazypay_make_request('query', payload=payload)
            
            # Log response safely, handling Unicode characters
            _logger.info(
                "Response of '/query' request for transaction with reference %s:\n%s",
                self.reference, _safe_log_data(query_data)
            )
            
            if query_data.get('result', {}).get('isSuccess'):
                payment_data = query_data.get('data', [{}])[0] if query_data.get('data') else {}
                status = payment_data.get('status', '').upper()
                is_paid = payment_data.get('isPaid', False)
                
                # Update transaction state based on status
                if is_paid or status == 'PAID':
                    self._set_done(state_message=_("Payment confirmed by EazyPay"))
                elif status == 'PENDING':
                    self._set_pending(state_message=_("Payment is pending"))
                elif status in ['FAILED', 'CANCELLED', 'CANCELED']:
                    error_msg = payment_data.get('errorMessage', 'Payment failed')
                    self._set_canceled(state_message=error_msg)
                else:
                    self._set_pending(state_message=_("Payment status: %s", status))
        except ValidationError as e:
            _logger.exception("Error querying payment status for transaction %s", self.reference)
            self._set_error(str(e))

