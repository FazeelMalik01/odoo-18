import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class InvoicePayController(http.Controller):

    @http.route(
        '/rental/pay/<int:invoice_id>',
        type='http',
        auth='public',
        website=True,
        csrf=False,
    )
    def pay_invoice_public(self, invoice_id, access_token=None, **kwargs):
        """Public invoice payment page — no login required."""

        invoice = request.env['account.move'].sudo().browse(invoice_id)

        if not invoice.exists() or invoice.move_type != 'out_invoice':
            return request.not_found()

        if not access_token or access_token != invoice.access_token:
            return request.not_found()

        providers = request.env['payment.provider'].sudo().search([
            ('state', 'in', ['enabled', 'test']),
            ('company_id', '=', invoice.company_id.id),
        ])

        partner = invoice.partner_id.sudo()

        stripe_publishable_key = ''
        for p in providers:
            if p.code == 'stripe':
                stripe_publishable_key = p.stripe_publishable_key or ''
                break

        return request.render('custom_rental.invoice_pay_public', {
            'invoice': invoice,
            'partner': partner,
            'access_token': access_token,
            'providers': providers,
            'amount': invoice.amount_residual,
            'currency': invoice.currency_id,
            'company': invoice.company_id,
            'stripe_publishable_key': stripe_publishable_key,
        })

    @http.route(
        '/rental/pay/create-transaction',
        type='json',
        auth='public',
        csrf=False,
    )
    def create_payment_transaction(self, invoice_id=None, access_token=None,
                                   provider_id=None, **kwargs):
        """Create payment transaction — public route, no session needed."""

        if not invoice_id or not access_token or not provider_id:
            return {'error': 'Missing required parameters'}

        invoice = request.env['account.move'].sudo().browse(invoice_id)

        if not invoice.exists():
            return {'error': 'Invoice not found'}

        if access_token != invoice.access_token:
            return {'error': 'Invalid access token'}

        if invoice.payment_state in ('paid', 'in_payment'):
            return {'error': 'Invoice is already paid'}

        provider = request.env['payment.provider'].sudo().browse(provider_id)
        if not provider.exists():
            return {'error': 'Payment provider not found'}

        try:
            # ── Get payment method for this provider ──────────
            payment_method = request.env['payment.method'].sudo().search([
                ('provider_ids', 'in', [provider_id]),
                ('active', '=', True),
            ], limit=1)

            if not payment_method:
                return {'error': 'No payment method configured for this provider.'}

            # ── Generate unique reference ─────────────────────
            reference = request.env['payment.transaction'].sudo()._compute_reference(
                provider.code,
                prefix=invoice.name.replace('/', '-'),
            )

            # ── Return URL after payment ──────────────────────
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
            return_url = f"{base_url}/rental/pay/status?access_token={access_token}"

            # ── Create the transaction ────────────────────────
            tx = request.env['payment.transaction'].sudo().create({
                'amount': invoice.amount_residual,
                'currency_id': invoice.currency_id.id,
                'partner_id': invoice.partner_id.id,
                'provider_id': provider_id,
                'payment_method_id': payment_method.id,
                'invoice_ids': [(6, 0, [invoice_id])],
                'reference': reference,
                'operation': 'online_redirect',
                'landing_route': return_url,
            })

            client_secret = ''
            redirect_url = ''

            # ── Stripe: get client_secret for Elements ────────
            if provider.code == 'stripe':
                try:
                    processing = tx._get_processing_values()
                    client_secret = processing.get('client_secret', '')
                    redirect_url = processing.get('redirect_url', '')
                    _logger.info("Stripe processing values: client_secret=%s redirect=%s",
                                 bool(client_secret), redirect_url)
                except Exception as e:
                    _logger.error("Failed to get Stripe processing values: %s", e)
                    return {'error': f'Stripe error: {str(e)}'}

            # ── Demo: simulate payment ────────────────────────
            elif provider.code == 'demo':
                try:
                    tx.sudo()._set_done()
                    tx.sudo()._reconcile_after_done()
                except Exception as e:
                    _logger.warning("Demo reconcile failed: %s", e)
                redirect_url = return_url + f'&tx_id={tx.id}'

            # ── Custom / Cash on Delivery ─────────────────────
            elif provider.code == 'custom':
                try:
                    tx.sudo().write({'state': 'pending'})
                except Exception as e:
                    _logger.warning("Custom state set failed: %s", e)
                redirect_url = return_url + f'&tx_id={tx.id}'

            # ── Other providers ───────────────────────────────
            else:
                try:
                    processing = tx._get_processing_values()
                    redirect_url = processing.get('redirect_url', return_url + f'&tx_id={tx.id}')
                except Exception as e:
                    _logger.warning("Processing values failed: %s", e)
                    redirect_url = return_url + f'&tx_id={tx.id}'

            return {
                'tx_id': tx.id,
                'reference': reference,
                'client_secret': client_secret,
                'redirect_url': redirect_url,
                'provider_code': provider.code,
            }

        except Exception as e:
            _logger.error("Transaction creation failed: %s", e)
            return {'error': str(e)}

    @http.route(
        '/rental/pay/stripe-confirm',
        type='json',
        auth='public',
        csrf=False,
    )
    def stripe_confirm(self, tx_id=None, access_token=None,
                       payment_intent_id=None, **kwargs):
        """Called after Stripe.js confirms — create validated payment on invoice."""

        if not tx_id:
            return {'error': 'Missing tx_id'}

        tx = request.env['payment.transaction'].sudo().browse(int(tx_id))
        if not tx.exists():
            return {'error': 'Transaction not found'}

        try:
            # ── Step 1: Fetch real PI from Stripe & update tx ─
            try:
                stripe_data = tx.provider_id._stripe_make_request(
                    f'payment_intents/{payment_intent_id}',
                    method='GET',
                )
                _logger.info("Stripe PI %s status=%s",
                             payment_intent_id, stripe_data.get('status'))
                tx._handle_notification_data('stripe', {'payment_intent': stripe_data})
            except Exception as e:
                _logger.warning("Stripe fetch/notify failed: %s — forcing done", e)
                tx.sudo().write({'state': 'done'})

            # ── Step 2: Ensure tx is done ─────────────────────
            if tx.state != 'done':
                _logger.warning("TX %s state=%s — forcing done", tx_id, tx.state)
                tx.sudo().write({'state': 'done'})

            # ── Step 3: Create validated payment per invoice ──
            for invoice in tx.invoice_ids:
                invoice.invalidate_recordset()

                if invoice.payment_state in ('paid', 'in_payment'):
                    _logger.info("Invoice %s already %s — skip",
                                 invoice.name, invoice.payment_state)
                    continue

                _logger.info("Creating payment for invoice %s amount=%s",
                             invoice.name, tx.amount)

                # Find bank journal (prefer 'bank' over 'cash')
                journal = request.env['account.journal'].sudo().search([
                    ('type', '=', 'bank'),
                    ('company_id', '=', invoice.company_id.id),
                ], limit=1) or request.env['account.journal'].sudo().search([
                    ('type', 'in', ['bank', 'cash']),
                    ('company_id', '=', invoice.company_id.id),
                ], limit=1)

                if not journal:
                    _logger.error("No bank/cash journal found for company %s",
                                  invoice.company_id.name)
                    continue

                _logger.info("Using journal: %s (id=%s type=%s)",
                             journal.name, journal.id, journal.type)

                # Prefer manual inbound payment method line
                payment_method_line = (
                    journal.inbound_payment_method_line_ids.filtered(
                        lambda l: l.code == 'manual'
                    )[:1]
                    or journal.inbound_payment_method_line_ids[:1]
                )

                payment_vals = {
                    'payment_type':  'inbound',
                    'partner_type':  'customer',
                    'partner_id':    invoice.partner_id.id,
                    'amount':        tx.amount,
                    'currency_id':   tx.currency_id.id,
                    'journal_id':    journal.id,
                    'memo':          f"{invoice.name} - {tx.reference}",
                    'date':          fields.Date.today(),
                }
                if payment_method_line:
                    payment_vals['payment_method_line_id'] = payment_method_line.id

                # Create & post (validate) the payment
                payment = request.env['account.payment'].sudo().create(payment_vals)
                payment.sudo().action_post()
                _logger.info("Payment %s posted (state=%s)", payment.name, payment.state)

                # Reconcile receivable lines
                invoice_lines = invoice.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                              and not l.reconciled
                )
                payment_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                              and not l.reconciled
                )

                _logger.info("Reconciling — invoice receivable lines: %d, payment: %d",
                             len(invoice_lines), len(payment_lines))

                if invoice_lines and payment_lines:
                    (invoice_lines + payment_lines).reconcile()
                    invoice.invalidate_recordset()
                    _logger.info("Invoice %s payment_state after reconcile: %s",
                                 invoice.name, invoice.payment_state)
                else:
                    _logger.warning(
                        "No receivable lines to reconcile.\n"
                        "  Invoice lines: %s\n  Payment lines: %s",
                        [(l.name, l.account_id.name, l.reconciled)
                         for l in invoice.line_ids],
                        [(l.name, l.account_id.name, l.reconciled)
                         for l in payment.move_id.line_ids],
                    )

            # ── Step 4: Return final state ─────────────────────
            invoice_payment_state = 'unknown'
            if tx.invoice_ids:
                tx.invoice_ids[0].invalidate_recordset()
                invoice_payment_state = tx.invoice_ids[0].payment_state

            _logger.info("stripe_confirm complete — tx: %s, invoice: %s",
                         tx.state, invoice_payment_state)

            return {
                'success':               True,
                'tx_state':              tx.state,
                'invoice_payment_state': invoice_payment_state,
            }

        except Exception as e:
            _logger.error("stripe_confirm failed for tx %s: %s", tx_id, e, exc_info=True)
            return {'error': str(e)}

    @http.route(
        '/rental/pay/status',
        type='http',
        auth='public',
        website=True,
        csrf=False,
    )
    def payment_status(self, tx_id=None, access_token=None, **kwargs):
        """Show payment status page."""

        tx = None
        invoice = None

        if tx_id:
            tx = request.env['payment.transaction'].sudo().browse(int(tx_id))
            if tx.exists() and tx.invoice_ids:
                invoice = tx.invoice_ids[0]

        return request.render('custom_rental.invoice_pay_status', {
            'tx': tx,
            'invoice': invoice,
        })
