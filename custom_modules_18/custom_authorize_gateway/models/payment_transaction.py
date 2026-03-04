# -*- coding: utf-8 -*-
"""
Extend payment.transaction to use CustomAuthorizeAPI and support full
Authorize.Net auth/capture payloads (lineItems, tax, duty, shipping, etc.).
"""

import logging
import pprint

from odoo import fields, models

from odoo.addons.payment_authorize.models.payment_transaction import PaymentTransaction as AuthorizePaymentTransaction
from odoo.addons.payment_authorize.models.authorize_request import AuthorizeAPI
from odoo.addons.custom_authorize_gateway.models.authorize_request import CustomAuthorizeAPI

_logger = logging.getLogger(__name__)


def _authorize_api(provider):
    """Use CustomAuthorizeAPI for Authorize.Net provider."""
    if provider.code == 'authorize':
        return CustomAuthorizeAPI(provider)
    return AuthorizeAPI(provider)


class PaymentTransaction(AuthorizePaymentTransaction):
    _inherit = 'payment.transaction'

    # Optional refId sent in createTransactionRequest (auth and capture).
    authorize_ref_id = fields.Char(
        string="Authorize Ref ID",
        help="Optional refId for Authorize.Net createTransactionRequest (e.g. 123456).",
    )
    # Optional full payload extras: lineItems, tax, duty, shipping, poNumber,
    # shipTo, userFields, processingOptions, subsequentAuthInformation,
    # authorizationIndicatorType. Stored as JSON; merged into transactionRequest.
    authorize_request_extra = fields.Json(
        string="Authorize Request Extra",
        help="Optional dict merged into the Authorize.Net transactionRequest. "
             "E.g. lineItems, tax, duty, shipping, shipTo, userFields, "
             "processingOptions, subsequentAuthInformation, authorizationIndicatorType.",
        default=lambda self: {},
    )

    def _authorize_create_transaction_request(self, opaque_data):
        """Use CustomAuthorizeAPI for auth/capture when creating from opaque data."""
        self.ensure_one()
        if self.provider_code != 'authorize':
            return super()._authorize_create_transaction_request(opaque_data)
        api = CustomAuthorizeAPI(self.provider_id)
        if self.provider_id.capture_manually or self.operation == 'validation':
            return api.authorize(self, opaque_data=opaque_data)
        return api.auth_and_capture(self, opaque_data=opaque_data)

    def _send_payment_request(self):
        """Use CustomAuthorizeAPI for token-based auth/auth_and_capture."""
        super()._send_payment_request()
        if self.provider_code != 'authorize':
            return
        if not self.token_id.authorize_profile:
            from odoo.exceptions import UserError
            from odoo import _
            raise UserError("Authorize.Net: " + _("The transaction is not linked to a token."))
        api = CustomAuthorizeAPI(self.provider_id)
        if self.provider_id.capture_manually:
            res_content = api.authorize(self, token=self.token_id)
            _logger.info(
                "authorize request response for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(res_content),
            )
        else:
            res_content = api.auth_and_capture(self, token=self.token_id)
            _logger.info(
                "auth_and_capture request response for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(res_content),
            )
        self._handle_notification_data('authorize', {'response': res_content})

    def _send_capture_request(self, amount_to_capture=None):
        """Use CustomAuthorizeAPI.capture with optional refId."""
        child_capture_tx = super()._send_capture_request(amount_to_capture=amount_to_capture)
        if self.provider_code != 'authorize':
            return child_capture_tx
        api = CustomAuthorizeAPI(self.provider_id)
        rounded_amount = round(self.amount, self.currency_id.decimal_places)
        ref_id = self.authorize_ref_id or self.reference
        res_content = api.capture(
            self.provider_reference, rounded_amount, ref_id=ref_id
        )
        _logger.info(
            "capture request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(res_content),
        )
        self._handle_notification_data('authorize', {'response': res_content})
        return child_capture_tx
