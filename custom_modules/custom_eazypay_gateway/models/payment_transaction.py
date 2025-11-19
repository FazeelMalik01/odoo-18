# -*- coding: utf-8 -*-

import logging
import pprint

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command

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
        
        # Generate unique invoice ID for EazyPay
        # EazyPay requires unique invoice IDs, so we append transaction ID and timestamp
        # Format: {reference}-{transaction_id}-{timestamp}
        # This ensures uniqueness even if the same sale order is paid multiple times
        import time
        import re
        
        # Sanitize reference to only alphanumeric and dashes (remove special characters)
        clean_reference = re.sub(r'[^a-zA-Z0-9-]', '', str(self.reference))
        
        timestamp = int(time.time() * 1000)  # Milliseconds timestamp
        unique_invoice_id = f"{clean_reference}-{self.id}-{timestamp}"
        
        # EazyPay might have length restrictions, so truncate if needed (max 50 chars typically)
        # But keep it readable by keeping the reference first
        if len(unique_invoice_id) > 50:
            # Keep reference and transaction ID, truncate timestamp if needed
            max_timestamp_len = 50 - len(clean_reference) - len(str(self.id)) - 2  # -2 for dashes
            if max_timestamp_len > 0:
                unique_invoice_id = f"{clean_reference}-{self.id}-{str(timestamp)[-max_timestamp_len:]}"
            else:
                # Fallback: use just reference and transaction ID
                unique_invoice_id = f"{clean_reference}-{self.id}"
        
        payload = {
            'appId': self.provider_id.eazypay_app_id,
            'invoiceId': unique_invoice_id,
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
                # The invoice ID from EazyPay might be in format: {reference}-{transaction_id}-{timestamp}
                # Try exact match first
                tx = self.search([
                    ('provider_code', '=', 'eazypay'),
                    ('reference', '=', invoice_id),
                ], limit=1)
                
                # If not found, try to match by extracting reference from invoice ID
                if not tx and '-' in invoice_id:
                    # Extract reference part (before first dash)
                    base_reference = invoice_id.split('-')[0]
                    tx = self.search([
                        ('provider_code', '=', 'eazypay'),
                        ('reference', '=', base_reference),
                    ], limit=1)
                    
                    # If still not found, try matching by transaction ID (second part)
                    if not tx and len(invoice_id.split('-')) >= 2:
                        try:
                            transaction_id = int(invoice_id.split('-')[1])
                            tx = self.search([
                                ('provider_code', '=', 'eazypay'),
                                ('id', '=', transaction_id),
                            ], limit=1)
                        except (ValueError, IndexError):
                            pass
        
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

    def _post_process(self):
        """ Override of `payment` to ensure invoices are created and posted for EazyPay transactions.
        
        This ensures that when a payment is successful:
        1. The sale order is confirmed (handled by sale module)
        2. Invoices are created automatically (always for EazyPay)
        3. Invoices are posted (set to 'posted' state)
        """
        # For EazyPay transactions, handle post-processing specially to avoid account_payment errors
        if self.provider_code == 'eazypay' and self.state == 'done':
            # Step 1: Confirm the sale order FIRST - this is critical
            confirmed_orders = self.env['sale.order']  # Initialize empty recordset
            if hasattr(self, '_check_amount_and_confirm_order'):
                confirmed_orders = self._check_amount_and_confirm_order()
                _logger.info(
                    "Confirmed %d order(s) for EazyPay transaction %s: %s",
                    len(confirmed_orders), self.reference, confirmed_orders.mapped('name') if confirmed_orders else 'None'
                )
            
            # Refresh to get updated order state
            self.invalidate_recordset(['sale_order_ids'])
            # Get all orders linked to this transaction
            all_orders = self.sale_order_ids
            # If no orders were confirmed yet, try to confirm them
            if not confirmed_orders and all_orders:
                for order in all_orders.filtered(lambda so: so.state in ('draft', 'sent')):
                    if order._is_confirmation_amount_reached():
                        order.with_context(send_email=True).action_confirm()
                        confirmed_orders |= order
                        _logger.info(
                            "Confirmed order %s for EazyPay transaction %s",
                            order.name, self.reference
                        )
            
            # Get confirmed orders
            confirmed_orders = self.sale_order_ids.filtered(lambda so: so.state == 'sale')
            
            if not confirmed_orders:
                _logger.warning(
                    "No confirmed orders found for EazyPay transaction %s. Orders: %s",
                    self.reference, self.sale_order_ids.mapped('name')
                )
            
            # Step 2: Create invoices for confirmed orders
            if confirmed_orders:
                if not self.invoice_ids:
                    _logger.info(
                        "Creating invoices for EazyPay transaction %s (orders: %s)",
                        self.reference, confirmed_orders.mapped('name')
                    )
                    
                    # Force all lines to be invoiceable
                    confirmed_orders._force_lines_to_invoice_policy_order()
                    
                    # Create final invoices for all confirmed orders
                    invoices = confirmed_orders.with_context(
                        raise_if_nothing_to_invoice=False
                    )._create_invoices(final=True)
                    
                    if invoices:
                        # Link invoices to the transaction
                        self.invoice_ids = [Command.set(invoices.ids)]
                        
                        # Setup access token for portal access
                        for invoice in invoices:
                            invoice._portal_ensure_token()
                        
                        _logger.info(
                            "Created %d invoice(s) for transaction %s: %s",
                            len(invoices), self.reference, invoices.mapped('name')
                        )
                    else:
                        _logger.warning(
                            "No invoices created for EazyPay transaction %s",
                            self.reference
                        )
                
                # Step 3: Post all invoices that are in draft state
                for invoice in self.invoice_ids.filtered(lambda inv: inv.state == 'draft'):
                    try:
                        invoice.action_post()
                        _logger.info(
                            "Posted invoice %s for transaction %s",
                            invoice.name, self.reference
                        )
                    except Exception as e:
                        _logger.exception(
                            "Error posting invoice %s for transaction %s: %s",
                            invoice.name, self.reference, e
                        )
            
            # Step 4: Create and post account payment (only once)
            # Ensure payment is created, posted, and reconciled with invoice
            if (
                self.operation != 'validation'
                and not self.payment_id
                and not any(child.state in ['done', 'cancel'] for child in self.child_transaction_ids)
            ):
                try:
                    # Try to create payment using standard method
                    payment = self.with_company(self.company_id)._create_payment()
                    if payment:
                        if payment.state == 'posted':
                            _logger.info(
                                "Created and posted payment %s for EazyPay transaction %s",
                                payment.name, self.reference
                            )
                        else:
                            # If payment was created but not posted, post it
                            payment.action_post()
                            _logger.info(
                                "Created and posted payment %s for EazyPay transaction %s",
                                payment.name, self.reference
                            )
                except ValidationError as e:
                    # Check if a draft payment was created before the error
                    # If so, delete it to prevent duplicates
                    draft_payments = self.env['account.payment'].search([
                        ('payment_transaction_id', '=', self.id),
                        ('state', '=', 'draft')
                    ])
                    if draft_payments:
                        draft_payments.unlink()
                        _logger.info(
                            "Removed %d draft payment(s) for EazyPay transaction %s before creating new one",
                            len(draft_payments), self.reference
                        )
                    # If payment method line is missing, create payment manually
                    if "payment method line" in str(e):
                        _logger.warning(
                            "Payment method line missing for EazyPay transaction %s. Creating payment manually.",
                            self.reference
                        )
                        
                        journal = self.provider_id.journal_id
                        payment_method_line = journal.inbound_payment_method_line_ids[:1]
                        
                        if payment_method_line:
                            reference = (f'{self.reference} - '
                                       f'{self.partner_id.display_name or ""} - '
                                       f'{self.provider_reference or ""}')
                            
                            payment_values = {
                                'amount': abs(self.amount),
                                'payment_type': 'inbound' if self.amount > 0 else 'outbound',
                                'currency_id': self.currency_id.id,
                                'partner_id': self.partner_id.commercial_partner_id.id,
                                'partner_type': 'customer',
                                'journal_id': journal.id,
                                'company_id': self.provider_id.company_id.id,
                                'payment_method_line_id': payment_method_line.id,
                                'payment_transaction_id': self.id,
                                'memo': reference,
                                'invoice_ids': self.invoice_ids,
                            }
                            
                            # Create payment and immediately link to transaction to prevent duplicates
                            payment = self.env['account.payment'].create(payment_values)
                            # Link to transaction BEFORE posting to prevent duplicate creation
                            self.payment_id = payment
                            # Now post the payment
                            payment.action_post()
                            
                            # Reconcile with invoices
                            if self.invoice_ids:
                                invoices = self.invoice_ids.filtered(lambda inv: inv.state == 'posted')
                                if invoices:
                                    payment_lines = payment.move_id.line_ids.filtered(
                                        lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
                                        and not line.reconciled
                                    )
                                    invoice_lines = invoices.line_ids.filtered(
                                        lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
                                        and not line.reconciled
                                    )
                                    all_lines = payment_lines + invoice_lines
                                    if all_lines:
                                        all_lines.reconcile()
                                        _logger.info(
                                            "Reconciled payment %s with invoices for EazyPay transaction %s",
                                            payment.name, self.reference
                                        )
                            
                            _logger.info(
                                "Created and posted payment %s manually for EazyPay transaction %s",
                                payment.name, self.reference
                            )
                    else:
                        _logger.warning(
                            "No payment method line in journal %s. Payment not created for EazyPay transaction %s",
                            journal.name if 'journal' in locals() else 'Unknown', self.reference
                        )
                    # Don't re-raise - payment creation is optional
                except Exception as payment_error:
                    _logger.exception(
                        "Error creating payment for EazyPay transaction %s: %s",
                        self.reference, payment_error
                    )
                    # Don't fail the whole process if payment creation fails
            
            # Mark as post-processed
            self.is_post_processed = True
        else:
            # For non-EazyPay transactions, use standard post-processing
            super()._post_process()

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

