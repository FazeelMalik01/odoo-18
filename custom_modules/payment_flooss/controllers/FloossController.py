# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

import urllib.parse

import werkzeug

from odoo import _, http, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.portal.controllers import portal

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class FloossController(http.Controller):
    _request_otp_url = '/payment/flooss/request_otp'
    _verify_otp_url = '/payment/flooss/verify_otp'
    _complete_url = '/payment/flooss/complete_order'
    _webhook_url = '/payment/flooss/webhook/'
    


    
    @http.route(_request_otp_url, type='json', auth='public', methods=['POST'])
    def flooss_request_otp(self, provider_id, phone):
        provider_sudo = request.env['payment.provider'].browse(provider_id).sudo()
        _logger.info("Flooss: OTP request received. Provider ID: %s, Phone: %s", provider_id, phone)
        response = provider_sudo._flooss_request_otp(phone)
        _logger.info("Flooss: OTP request response: %s", response)
        return response

    @http.route('/payment/flooss/create_transaction', type='json', auth='public', methods=['POST'])
    def create_flooss_transaction(self, provider_id, amount):
        provider_sudo = request.env['payment.provider'].browse(provider_id).sudo()

        # Create a new transaction
        tx_sudo = request.env['payment.transaction'].sudo().create({
            'acquirer_id': provider_sudo.id,
            'amount': amount,
            'currency_id': provider_sudo.currency_id.id,
            'reference': request.env['payment.transaction']._generate_reference(),
            'state': 'draft',
            'provider_code': 'flooss',
            'partner_id': request.env.user.partner_id.id,
        })

        return {'tx_reference': tx_sudo.reference, 'amount': tx_sudo.amount}

    @http.route('/payment/flooss/verify_otp', type='json', auth='public', methods=['POST'])
    def flooss_verify_otp(self, provider_id, phone, otp, tx_reference=None):
        provider_sudo = request.env['payment.provider'].browse(provider_id).sudo()
        _logger.info("Flooss: OTP verification started. Provider ID: %s, Phone: %s, Tx Reference: %s", provider_id, phone, tx_reference)
        
        # Encrypt OTP
        try:
            encrypted_otp = provider_sudo._flooss_encrypt_otp(otp)
            _logger.info("Flooss Encrypted OTP: %s", encrypted_otp)

        except ValidationError as e:
            return {'verify': None, 'payment_request': None, 'error': str(e)}

        _logger.debug("Flooss: Encrypted OTP: %s", encrypted_otp)

        # Call verify OTP API
        try:
            verify_response = provider_sudo._flooss_verify_otp(phone, encrypted_otp)
            
            # If API returned string instead of dict, wrap in dict
            if isinstance(verify_response, str):
                verify_response = {'message': verify_response}

        except ValidationError as e:
            # This happens when API returns HTTP 417, 400 etc.
            verify_response = None
            return {'verify': None, 'payment_request': None, 'error': str(e)}
        except Exception as e:
            verify_response = None
            _logger.exception("Unexpected error verifying OTP: %s", e)
            return {'verify': None, 'payment_request': None, 'error': str(e)}

        _logger.info("Flooss: OTP verification response: %s", verify_response)
        return {
        'verify': verify_response,
        'error': None
    }

    @http.route(_complete_url, type='json', auth='public', methods=['POST'])
    def flooss_complete_order(self, provider_id, reference_id, phone=None, amount=None):
        provider_sudo = request.env['payment.provider'].browse(provider_id).sudo()
        response = provider_sudo._flooss_check_status(reference_id, phone=phone, amount=amount)
        normalized = self._normalize_flooss_data(response)
        try:
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data('flooss', normalized)
            tx_sudo._handle_notification_data('flooss', normalized)
        except ValidationError:
            _logger.warning("Flooss: unable to find transaction for reference %s, skipping handle.", reference_id)
        return response

    def action_flooss_create_webhook(self):
        raise ValidationError(_("Flooss does not support webhook creation via API. Please configure the webhook URL manually in your Flooss merchant portal."))

    def _normalize_flooss_data(self, data, from_webhook=False):
        result = {}
        if from_webhook:
            result = {
                'reference_id': data.get('transactionNumber'),
                'status': data.get('status'),
                'id': data.get('transactionNumber'),
            }
        else:
            if isinstance(data, dict) and data.get('data') and isinstance(data.get('data'), dict):
                d = data.get('data')
                result = {
                    'reference_id': d.get('referenceId') or d.get('id'),
                    'status': data.get('status') or data.get('message') or 'UNKNOWN',
                    'id': d.get('referenceId') or d.get('id'),
                    **d,
                }
            else:
                result = {
                    'reference_id': data.get('referenceId') or data.get('id'),
                    'status': data.get('status') or data.get('message') or 'UNKNOWN',
                    'id': data.get('referenceId') or data.get('id'),
                }
        return result

    def _verify_notification_origin(self, notification_data, tx_sudo):
        headers = request.httprequest.headers
        auth_header = headers.get('Authorization') or headers.get('authorization') or ''
        bearer = None
        if auth_header.startswith('Bearer '):
            bearer = auth_header.split(' ', 1)[1].strip()
        provider = tx_sudo.provider_id if tx_sudo else None
        expected = provider.flooss_notify_jwt if provider and hasattr(provider, 'flooss_notify_jwt') else None
        if expected:
            if bearer != expected:
                _logger.warning("FLOOSS webhook Authorization mismatch. Received: %s, Expected: %s", bearer, expected)
                raise Forbidden()
        else:
            _logger.warning("FLOOSS webhook notify token not configured on provider %s.", provider.id if provider else 'unknown')

    # Corrected Controller Code

    @http.route('/payment/flooss/proceed_payment', type='json', auth='public', website=True, methods=['POST'])
    def flooss_proceed_payment(self, provider_id, phone, tx_reference):
        """Process Flooss payment and return success data for frontend redirect"""
        try:
            provider_sudo = request.env['payment.provider'].browse(provider_id).sudo()
            sale_order_id = request.website.sale_get_order()

            if not sale_order_id:
                return {'error': 'No active order found'}

            # Handle transaction creation/retrieval - SIMPLIFIED LOGIC
            payment_transaction = request.env['payment.transaction'].sudo().search([
                ('reference', '=', tx_reference)
            ], limit=1)

            if not payment_transaction:
                payment_transaction = request.env['payment.transaction'].sudo().create({
                    'provider_id': provider_sudo.id,
                    'payment_method_id': provider_sudo.payment_method_ids[
                        0].id if provider_sudo.payment_method_ids else False,
                    'reference': tx_reference,
                    'amount': sale_order_id.amount_total,
                    'currency_id': sale_order_id.currency_id.id,
                    'partner_id': sale_order_id.partner_id.id,
                    'sale_order_ids': [(4, sale_order_id.id)],
                })

            try:
                # Call Flooss API
                payment_request_resp = provider_sudo._flooss_send_payment_request(payment_transaction, phone)
                response_code = payment_request_resp.get('code')
                error_message = payment_request_resp.get('message')
                if response_code == 0:
                    if error_message == "Success":
                        ref_id = payment_request_resp.get('data', {}).get('referenceId')
                        transaction_id = payment_request_resp.get('data', {}).get('id')
                        created_at_flooss = payment_request_resp.get('data', {}).get('createdAt')
                        status = payment_request_resp.get('message')

                        # Update transaction with Flooss data
                        payment_transaction.write({
                            'flooss_type': 'ONLINE_CHECKOUT',
                            'flooss_reference_id': ref_id,
                            'flooss_created_at': created_at_flooss,
                            'flooss_transaction_id': created_at_flooss,
                            'flooss_payment_status': status,
                            'state': 'done',
                            'provider_reference': f'FLOOSS_{sale_order_id.name}_{tx_reference}',
                        })
                        # Confirm the sale order if needed
                        # if sale_order_id.state in ['draft', 'sent']:
                        #     sale_order_id.sudo().action_confirm()
                        # Create payment request data
                        payment_request = {
                            'order_id': f'FLOOSS_{sale_order_id.id}_{sale_order_id.name}',
                            'reference': payment_transaction.reference,
                            'amount': float(sale_order_id.amount_total),
                            'currency': sale_order_id.currency_id.name,
                            'order_number': sale_order_id.name,
                            'transaction_id': payment_transaction.id,
                            'merchantOrderId': sale_order_id.name,
                        }
                        redirect_url = f'/payment/thank-you?amount={sale_order_id.amount_total}&currency={sale_order_id.currency_id.symbol}&order_number={sale_order_id.name}&tx_ref={tx_reference}&payment_method=flooss&status=success'

                        return {
                            'success': True,
                            'payment_request': payment_request,
                            'redirect_url': redirect_url,
                            'message': 'Payment processed successfully',
                            'provider': 'Flooss Payment Gateway'
                        }
                    else:
                        return {'error': 'Technical Error (9), please contact Flooss Support @13310055 for assistance'}

                elif response_code == -1:
                    _logger.error("Flooss payment failed - Code: -1 (Error), Data: null")
                    return {'error': 'Flooss payment failed - Code: -1 (Error), Data: null'}

                elif response_code == 21:
                    _logger.error(
                        "Flooss Error Code: 21 - Technical Error (1), please contact store for assistance. (Entered merchant transaction type is not allowed)")
                    return {
                        'error': 'Technical Error (1), please contact store for assistance. (Entered merchant transaction type is not allowed)'}

                elif response_code == 35:
                    _logger.error(
                        "Flooss Error Code: 35 - This phone number does not exist on FLOOSS. Please try again. (phone number does not exist)")
                    return {'error': 'This phone number does not exist on FLOOSS. Please try again.'}

                elif response_code == 36:
                    _logger.error(
                        "Flooss Error Code: 36 - Your Flooss account is not active. Please contact Flooss support @13310055 for assistance. (FLOOSS account is not active)")
                    return {
                        'error': 'Your Flooss account is not active. Please contact Flooss support @13310055 for assistance.'}

                elif response_code == 37:
                    _logger.error(
                        "Flooss Error Code: 37 - Please repay your overdue installments before making a purchase (1) (If client account is on hold due to late payments)")
                    return {'error': 'Please repay your overdue installments before making a purchase'}

                elif response_code == 38:
                    _logger.error(
                        "Flooss Error Code: 38 - Due to late payments, please wait {number of days} days to make a new purchase (user did late payments and is now in cooldown state)")
                    return {'error': 'Due to late payments, please wait {number of days} days to make a new purchase'}

                elif response_code == 42:
                    _logger.error(
                        "Flooss Error Code: 42 - Due to late payments, please wait {number of days} days to make a new purchase (user did late payments and is now in cooldown state)")
                    return {'error': 'Due to late payments, please wait {number of days} days to make a new purchase'}

                elif response_code == 39:
                    _logger.error(
                        "Flooss Error Code: 39 - Please apply for Flooss Split on the Flooss app, then return to checkout to complete your purchase. (If user does not have active BNPL)")
                    return {
                        'error': 'Please apply for Flooss Split on the Flooss app, then return to checkout to complete your purchase.'}

                elif response_code == 40:
                    _logger.error(
                        "Flooss Error Code: 40 - Technical Error (2), please contact Flooss Support @13310055 for assistance (User's Application is not in valid state)")
                    return {'error': 'Technical Error (2), please contact Flooss Support @13310055 for assistance'}

                elif response_code == 23:
                    _logger.error(
                        "Flooss Error Code: 23 - Technical Error (3), please contact Flooss Support @13310055 for assistance (If application is not active)")
                    return {'error': 'Technical Error (3), please contact Flooss Support @13310055 for assistance'}

                elif response_code == 31:
                    _logger.error(
                        "Flooss Error Code: 31 - Technical Error (11), please contact Flooss Support @13310055 for assistance (If no QR is found)")
                    return {'error': 'Technical Error (11), please contact Flooss Support @13310055 for assistance'}

                elif response_code == 41:
                    _logger.error(
                        "Flooss Error Code: 41 - Please repay your overdue installments before making a purchase (2) (If user wallet status is on hold)")
                    return {'error': 'Please repay your overdue installments before making a purchase'}

                elif response_code == 43:
                    _logger.error(
                        "Flooss Error Code: 43 - Renew your residency permit to proceed, please contact Flooss Support @13310055 for assistance (User's credit wallet status is RP_BLOCKED)")
                    return {
                        'error': 'Renew your residency permit to proceed, please contact Flooss Support @13310055 for assistance'}

                elif response_code == 44:
                    _logger.error(
                        "Flooss Error Code: 44 - Floossi Limit is not active, please contact Flooss Support @13310055 for assistance (User's credit wallet is not in Active state)")
                    return {
                        'error': 'Floossi Limit is not active, please contact Flooss Support @13310055 for assistance'}

                elif response_code == 45:
                    _logger.error(
                        "Flooss Error Code: 45 - Minimum Floossi Limit of 10 BHD is required to make a purchase (Wallet balance is low)")
                    return {'error': 'Minimum Floossi Limit of 10 BHD is required to make a purchase'}

                elif response_code == 46:
                    _logger.error(
                        "Flooss Error Code: 46 - Maximum purchase amount is 1000 BHD (Purchase limit is exceeded)")
                    return {'error': 'Maximum purchase amount is 1000 BHD'}

                elif response_code == 29:
                    _logger.error(
                        "Flooss Error Code: 29 - Technical Error (9), please contact Flooss Support @13310055 for assistance (User has a pending Flooss Split application that needs to be completed or cancelled)")
                    return {'error': 'Technical Error (9), please contact Flooss Support @13310055 for assistance'}

                elif response_code == 30:
                    _logger.error(
                        "Flooss Error Code: 30 - Technical Error (10), please contact Flooss Support @13310055 for assistance (If user wallet not found)")
                    return {'error': 'Technical Error (10), please contact Flooss Support @13310055 for assistance'}

                elif response_code == 49:
                    _logger.error(
                        "Flooss Error Code: 49 - Unable to proceed due to status of existing finance, please contact Flooss Support @13310055 for assistance (If user has any loan with Legal or Legal overdue status)")
                    return {
                        'error': 'Unable to proceed due to status of existing finance, please contact Flooss Support @13310055 for assistance'}

                elif response_code == 50:
                    _logger.error(
                        "Flooss Error Code: 50 - User not found, please contact store for assistance (provided phone number is not correct and cannot be found in the system)")
                    return {'error': 'User not found, please contact store for assistance'}

                elif response_code == 51:
                    _logger.error(
                        "Flooss Error Code: 51 - Unable to proceed, please contact Flooss Support @13310055 for assistance (If user is marked as blacklisted)")
                    return {'error': 'Unable to proceed, please contact Flooss Support @13310055 for assistance'}

                elif response_code == 32:
                    _logger.error(
                        "Flooss Error Code: 32 - Technical Error (12), please contact Flooss Support @13310055 (If Merchant Id or Phone number is not correct)")
                    return {'error': 'Technical Error (12), please contact Flooss Support @13310055'}

                elif response_code == 33:
                    _logger.error(
                        "Flooss Error Code: 33 - Technical Error (13), please contact Flooss Support @13310055 (Previous FLOOSS Split application with the same wallet is not found)")
                    return {'error': 'Technical Error (13), please contact Flooss Support @13310055'}

                elif response_code == 34:
                    _logger.error(
                        "Flooss Error Code: 34 - Technical Error (14), please contact Flooss Support @13310055 (Application associated with different wallet)")
                    return {'error': 'Technical Error (14), please contact Flooss Support @13310055'}
                else:
                    error_message = payment_request_resp.get('message', 'Unknown error occurred please contact store for assistance')
                    return {'error': f'Payment request failed: {error_message}'}

            except Exception as e:
                _logger.exception("Error sending Flooss payment request: %s", e)
                return {'error': f'Payment request failed: {str(e)}'}

        except Exception as e:
            _logger.exception("Error in flooss_proceed_payment: %s", e)
            return {'error': f'Payment processing failed: {str(e)}'}

    @http.route('/payment/thank-you', type='http', auth='public', website=True)
    def payment_thank_you(self, **kwargs):
        """Thank you page after successful payment"""
        try:
            # Extract parameters from URL
            amount = kwargs.get('amount', '')
            currency = kwargs.get('currency', '$')
            order_number = kwargs.get('order_number', '')
            tx_reference = kwargs.get('tx_ref', '')
            payment_method = kwargs.get('payment_method', 'Flooss').title()
            status = kwargs.get('status', 'success')

            # Get additional order details if transaction reference exists
            order_details = {}
            transaction = None

            if tx_reference:
                transaction = request.env['payment.transaction'].sudo().search([
                    ('reference', '=', tx_reference)
                ], limit=1)

                if transaction and transaction.sale_order_ids:
                    order = transaction.sale_order_ids[0]
                    order_details = {
                        'order': order,
                        'order_lines': order.order_line,
                        'partner': order.partner_id,
                        'order_date': order.date_order,
                        'total_amount': order.amount_total,
                    }

            # Prepare template values
            values = {
                'amount': amount,
                'currency': currency,
                'order_number': order_number,
                'tx_reference': tx_reference,
                'payment_method': payment_method,
                'status': status,
                'transaction': transaction,
                'order_details': order_details,
                'page_title': 'Thank You - Payment Successful',
                'current_datetime': fields.Datetime.now(),
            }

            _logger.info("Thank you page rendered for order: %s", order_number)

            # Render the thank you template
            return request.render('payment_flooss.payment_thank_you_template', values)

        except Exception as e:
            _logger.error("Error rendering thank you page: %s", str(e))

            # Fallback to simple success message
            fallback_values = {
                'amount': kwargs.get('amount', ''),
                'currency': kwargs.get('currency', '$'),
                'order_number': kwargs.get('order_number', ''),
                'error_occurred': True,
                'error_message': 'Payment was successful, but some details could not be loaded.'
            }
            return request.render('payment_flooss.payment_thank_you_simple', fallback_values)

    @http.route('/payment/flooss/check_status', type='json', auth='public',website=True, methods=['POST'])
    def check_payment_status(self, tx_reference, **kwargs):
        try:
            payment_id = request.env['payment.transaction'].sudo().search([
                ('reference', '=', tx_reference)
            ], limit=1)

            if not payment_id:
                return {'error': 'Transaction not found'}

            provider_sudo = request.env['payment.provider'].browse(payment_id.provider_id.id).sudo()
            floss_ref = payment_id.flooss_reference_id
            floss_phone = payment_id.partner_phone
            payment_transaction = payment_id.amount
            sale_order = payment_id.sale_order_ids[:1]
            merchant_order_id = sale_order.name if sale_order else payment_id.reference
            payload = {
                'phoneNumber': floss_phone,
                'transactionAmount': float(payment_transaction),
                'referenceId': floss_ref,
                'merchantOrderId': merchant_order_id,
            }
            return provider_sudo._flooss_make_request(
                '/pie/api/v1/bo/merchants/online-checkout/status',
                json_payload=payload,
                method='GET'
            )
        except Exception as e:
            return {'error': str(e)}


    @http.route('/payment/flooss/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def flooss_webhook(self, **kwargs):
        payload = request.get_json_data()
        _logger.info("Flooss Webhook called. Payload: %s", payload)

        transaction_number = payload.get("transactionNumber")
        status = payload.get("status")
        merchant_order_id = payload.get("merchantOrderId")

        if not transaction_number:
            return {"error": "Missing transactionNumber"}

        transaction = request.env['payment.transaction'].sudo().search([
            ('flooss_reference_id', '=', str(transaction_number))
        ], limit=1)

        if not transaction:
            return {"error": f"Transaction {transaction_number} not found"}

        transaction.write({
        'flooss_webhook_payload': str(payload),
        'flooss_merchant_order_id': merchant_order_id,
        })

        if status == "SUCCESS":
            transaction.write({
                'state': 'done',
                'flooss_payment_status': 'SUCCESS',
            })
            transaction.sale_order_ids.write({'state': 'sale'})
        else:
            transaction.write({
                'state': 'error',
                'flooss_payment_status': status,
            })

        return {"result": "Webhook processed"}

