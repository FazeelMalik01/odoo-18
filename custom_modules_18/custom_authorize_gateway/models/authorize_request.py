# -*- coding: utf-8 -*-
"""
Extended Authorize.Net API with full auth and capture payload support.

Implements:
- Authorize a Credit Card (authOnlyTransaction) with full payload:
  lineItems, tax, duty, shipping, poNumber, customer, billTo, shipTo,
  customerIP, userFields, processingOptions, subsequentAuthInformation,
  authorizationIndicatorType.
- Capture a Previously Authorized Amount (priorAuthCaptureTransaction) with refId.
"""

import logging
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_authorize.models.authorize_request import AuthorizeAPI

_logger = logging.getLogger(__name__)


class CustomAuthorizeAPI(AuthorizeAPI):
    """
    Extended Authorize.Net API that supports full createTransactionRequest payloads
    for authOnlyTransaction and priorAuthCaptureTransaction.
    """

    def _get_authorize_request_extra(self, tx):
        """
        Get optional extra payload to merge into transactionRequest (lineItems,
        tax, duty, shipping, shipTo, userFields, processingOptions,
        subsequentAuthInformation, authorizationIndicatorType, etc.).
        Source: tx.authorize_request_extra if the field exists and is set.
        """
        if hasattr(tx, 'authorize_request_extra') and tx.authorize_request_extra:
            return dict(tx.authorize_request_extra)
        return {}

    def _prepare_authorization_transaction_request(self, transaction_type, tx_data, tx):
        """
        Build full auth transaction request and merge optional extra payload
        (lineItems, tax, duty, shipping, poNumber, shipTo, userFields, etc.).
        """
        base = super()._prepare_authorization_transaction_request(
            transaction_type, tx_data, tx
        )
        tr = dict(base.get('transactionRequest', {}))
        extra = self._get_authorize_request_extra(tx)
        # Merge extra into transactionRequest (extra can override base)
        for key, value in extra.items():
            if value is not None:
                tr[key] = value
        return {'transactionRequest': tr}

    def authorize(self, tx, token=None, opaque_data=None):
        """
        Authorize (authOnlyTransaction) with full API support: refId and
        optional lineItems, tax, duty, shipping, shipTo, userFields,
        processingOptions, subsequentAuthInformation, authorizationIndicatorType.
        """
        tx_data = self._prepare_tx_data(token=token, opaque_data=opaque_data)
        tr_request = self._prepare_authorization_transaction_request(
            'authOnlyTransaction', tx_data, tx
        )
        data = {
            'refId': getattr(tx, 'authorize_ref_id', None) or tx.reference or '',
            **tr_request,
        }
        response = self._make_request('createTransactionRequest', data)
        return self._format_response(response, 'auth_only')

    def auth_and_capture(self, tx, token=None, opaque_data=None):
        """
        Auth and capture with full auth payload support (same extra fields as authorize).
        """
        tx_data = self._prepare_tx_data(token=token, opaque_data=opaque_data)
        tr_request = self._prepare_authorization_transaction_request(
            'authCaptureTransaction', tx_data, tx
        )
        data = {
            'refId': getattr(tx, 'authorize_ref_id', None) or tx.reference or '',
            **tr_request,
        }
        response = self._make_request('createTransactionRequest', data)
        result = self._format_response(response, 'auth_capture')
        errors = response.get('transactionResponse', {}).get('errors')
        if errors:
            result['x_response_reason_text'] = '\n'.join(
                [e.get('errorText') for e in errors]
            )
        return result

    def capture(self, transaction_id, amount, ref_id=None):
        """
        Capture a previously authorized amount (priorAuthCaptureTransaction)
        with optional refId.

        :param str transaction_id: id of the authorized transaction (refTransId)
        :param str amount: amount to capture
        :param str ref_id: optional refId for the request
        :return: response dict with x_response_code, x_trans_id, etc.
        """
        payload = {
            'transactionRequest': {
                'transactionType': 'priorAuthCaptureTransaction',
                'amount': str(amount),
                'refTransId': transaction_id,
            }
        }
        if ref_id is not None:
            payload['refId'] = ref_id
        response = self._make_request('createTransactionRequest', payload)
        return self._format_response(response, 'prior_auth_capture')

    def charge_opaque_data(self, partner, amount, descriptor, value, transaction_type='auth_capture'):
        """
        Charge a card using an opaque data nonce from Accept.js, without
        requiring an existing payment.transaction record.

        :param partner: res.partner record (for billTo info)
        :param float amount: amount to charge
        :param str descriptor: opaqueData.dataDescriptor from Accept.js
        :param str value: opaqueData.dataValue from Accept.js
        :param str transaction_type: 'auth_capture' or 'auth_only'
        :return: dict with x_response_code, x_trans_id, x_response_reason_text
        """
        tx_type = 'authCaptureTransaction' if transaction_type == 'auth_capture' else 'authOnlyTransaction'

        opaque_data = {
            'dataDescriptor': descriptor,
            'dataValue': value,
        }

        payload = {
            'transactionRequest': {
                'transactionType': tx_type,
                'amount': str(round(amount, 2)),
                'payment': {
                    'opaqueData': opaque_data,
                },
                'billTo': {
                    'firstName': (partner.name or '').split(' ')[0][:50],
                    'lastName': ' '.join((partner.name or '').split(' ')[1:])[:50] or '.',
                    'address': (partner.street or '')[:60],
                    'city': (partner.city or '')[:40],
                    'state': (partner.state_id.code or '')[:40],
                    'zip': (partner.zip or '')[:20],
                    'country': (partner.country_id.code or '')[:60],
                    'email': (partner.email or '')[:255],
                },
            }
        }

        response = self._make_request('createTransactionRequest', payload)
        result = self._format_response(response, 'auth_capture' if transaction_type == 'auth_capture' else 'auth_only')

        # Surface transaction-level errors if any
        errors = response.get('transactionResponse', {}).get('errors')
        if errors:
            result['error'] = '\n'.join(e.get('errorText', '') for e in errors)
        elif result.get('x_response_code') not in ('1',):
            result['error'] = result.get('x_response_reason_text') or 'Transaction declined.'

        return result