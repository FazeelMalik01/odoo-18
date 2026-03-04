# -*- coding: utf-8 -*-

import hashlib
import hmac
import logging
import pprint
import time

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('eazypay', 'EazyPay')],
        ondelete={'eazypay': 'set default'}
    )
    
    eazypay_app_id = fields.Char(
        string="EazyPay App ID",
        help="Your EazyPay application ID",
        required_if_provider='eazypay',
    )
    
    eazypay_secret_key = fields.Char(
        string="EazyPay Secret Key",
        help="Your EazyPay secret key for generating HMAC signatures",
        required_if_provider='eazypay',
        groups='base.group_system',
    )
    
    eazypay_payment_methods = fields.Char(
        string="Payment Methods",
        help="Comma-separated list of payment methods (e.g., BENEFITGATEWAY,CREDITCARD,APPLEPAY)",
        default="BENEFITGATEWAY,CREDITCARD,APPLEPAY",
        required_if_provider='eazypay',
    )

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'eazypay').update({
            'support_refund': 'none',
            'support_tokenization': False,
            'support_manual_capture': None,  # Selection field doesn't support 'none', use None instead
        })

    # === BUSINESS METHODS === #

    def _eazypay_make_request(self, endpoint, payload=None, method='POST'):

        self.ensure_one()

        url = f'https://api.eazy.net/merchant/checkout/{endpoint}'
        
        # Generate timestamp and secret hash
        timestamp = int(time.time() * 1000)  # milliseconds
        
        # Generate secret hash based on endpoint
        if endpoint == 'createInvoice':
            # For createInvoice: HMAC-SHA256(timestamp + currency + amount + appId)
            text = str(timestamp) + payload.get('currency', '') + str(payload.get('amount', '')) + self.eazypay_app_id
        elif endpoint == 'query':
            # For query: HMAC-SHA256(timestamp + appId)
            text = str(timestamp) + self.eazypay_app_id
        else:
            text = str(timestamp) + self.eazypay_app_id
        
        secret_hash = hmac.new(
            self.eazypay_secret_key.encode('utf-8'),
            text.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'Content-Type': 'application/json',
            'Timestamp': str(timestamp),
            'Secret-Hash': secret_hash,
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload),
                )
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('result', {}).get('description', 'Unknown error')
                raise ValidationError(_("EazyPay: %s", error_msg))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(_("EazyPay: Could not establish the connection to the API."))
        
        return response.json()

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'eazypay':
            # EazyPay supports multiple currencies, but BHD is common
            # You can filter specific currencies here if needed
            pass
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'eazypay':
            return default_codes
        # Return the EazyPay payment method code
        return {'eazypay'}


