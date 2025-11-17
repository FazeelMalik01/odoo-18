# -*- coding: utf-8 -*-

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class EazyPayController(http.Controller):
    _return_url = '/payment/eazypay/return/<string:global_transaction_id>'
    _webhook_url = '/payment/eazypay/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def eazypay_return(self, global_transaction_id, **kwargs):
        """ Process the return from EazyPay after payment.

        :param str global_transaction_id: The global transaction ID from EazyPay URL.
        :param dict kwargs: Additional data from the return request.
        :return: Redirection to the payment status page.
        :rtype: werkzeug.wrappers.Response
        """
        _logger.info(
            "EazyPay return with global_transaction_id %s and data:\n%s",
            global_transaction_id, kwargs
        )

        if not global_transaction_id:
            _logger.warning("EazyPay return received without global transaction ID")
            return request.redirect('/payment/process')

        # EazyPay concatenates the transaction ID to the placeholder instead of replacing it
        # So we get: EAZY_GLOBAL_TRN_ID{actual_id} instead of just {actual_id}
        # Strip the prefix if present
        if global_transaction_id.startswith('EAZY_GLOBAL_TRN_ID'):
            global_transaction_id = global_transaction_id.replace('EAZY_GLOBAL_TRN_ID', '', 1)
            _logger.info("EazyPay return - Stripped prefix, actual ID: %s", global_transaction_id)

        # Find the transaction
        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('provider_code', '=', 'eazypay'),
            ('eazypay_global_transaction_id', '=', global_transaction_id),
        ], limit=1)

        if not tx_sudo:
            _logger.warning(
                "Received return for unknown transaction with global_transaction_id %s",
                global_transaction_id
            )
            return request.redirect('/payment/process')

        # Query payment status and update transaction state
        tx_sudo._eazypay_query_payment_status()
        
        # Get the sale order linked to this transaction
        # The sale module adds sale_order_ids field to payment.transaction
        order = tx_sudo.sale_order_ids[:1] if hasattr(tx_sudo, 'sale_order_ids') and tx_sudo.sale_order_ids else None
        
        # If payment is successful, trigger post-processing
        # The sale module's _post_process will automatically confirm the order
        if tx_sudo.state == 'done':
            # Trigger post-processing - this will confirm the sale order automatically
            if not tx_sudo.is_post_processed:
                try:
                    tx_sudo._post_process()
                except Exception as e:
                    # Log the error but continue - the order might still be confirmed
                    # Invoice creation might fail due to missing payment method lines in journal
                    _logger.exception(
                        "Error during post-processing for transaction %s: %s",
                        tx_sudo.reference, e
                    )
            
            # Refresh the order to get updated state
            if order:
                order.invalidate_recordset(['state'])
        
        # Use /shop/payment/validate route which handles the redirect properly
        # This route will:
        # 1. Get the order from session
        # 2. Get the transaction from the order
        # 3. Redirect to /shop/confirmation which shows the order
        landing_route = '/shop/payment/validate'
        
        # If we have an order, ensure it's in the session
        if order:
            request.session['sale_last_order_id'] = order.id
        
        # Redirect to the landing route
        return request.redirect(landing_route)

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def eazypay_webhook(self, **kwargs):
        """ Process the webhook notification from EazyPay.

        :param dict kwargs: The notification data sent by EazyPay.
        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        _logger.info("EazyPay webhook received with data:\n%s", kwargs)

        # Get JSON data from request
        data = request.get_json_data()
        
        if not data:
            # Try to get from kwargs
            data = kwargs

        # Extract global transaction ID
        global_transaction_id = data.get('globalTransactionsId') or data.get('globalTransactionId')
        
        if not global_transaction_id:
            _logger.warning("EazyPay webhook received without global transaction ID")
            return request.make_json_response('')

        # Find the transaction
        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('provider_code', '=', 'eazypay'),
            ('eazypay_global_transaction_id', '=', global_transaction_id),
        ], limit=1)

        if not tx_sudo:
            _logger.warning(
                "Received webhook for unknown transaction with global_transaction_id %s",
                global_transaction_id
            )
            return request.make_json_response('')

        # Process the notification
        try:
            tx_sudo._handle_notification_data('eazypay', data)
        except Exception as e:
            _logger.exception("Error processing EazyPay webhook: %s", e)

        return request.make_json_response('')

