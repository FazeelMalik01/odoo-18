import logging
from odoo import http
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
    def pay_invoice_public(self, invoice_id, access_token=None, flow=None, **kwargs):
        """Public invoice payment page — no login required.

        flow='remaining' → sent after a partial payment, only show full remaining amount.
        flow='quote' or None → new quote, show Pay in Full + Pay 30% Deposit options.
        """

        invoice = request.env['account.move'].sudo().browse(invoice_id)

        if not invoice.exists() or invoice.move_type != 'out_invoice':
            return request.not_found()

        if not access_token or access_token != invoice.access_token:
            return request.not_found()

        providers = request.env['payment.provider'].sudo().search([
            ('state', 'in', ['enabled', 'test']),
            ('company_id', 'in', [invoice.company_id.id, False]),
            ('code', '=', 'ipos_pay'),
        ])
        _logger.info(
            "[Rental InvoicePay] pay_invoice_public invoice=%s company=%s providers=%s token_ok=%s flow=%s",
            invoice.id, invoice.company_id.id, providers.mapped('id'), bool(access_token), flow,
        )

        partner = invoice.partner_id.sudo()

        # For remaining-balance invoices only the full residual is shown; no deposit split.
        show_deposit_option = (flow != 'remaining')
        deposit_amount = round(invoice.amount_total * 0.30, 2) if show_deposit_option else 0.0

        return request.render('custom_rental.invoice_pay_public', {
            'invoice': invoice,
            'invoice_ref': invoice.invoice_origin or '',
            'partner': partner,
            'access_token': access_token,
            'providers': providers,
            'amount': invoice.amount_residual,
            'deposit_amount': deposit_amount,
            'show_deposit_option': show_deposit_option,
            'currency': invoice.currency_id,
            'company': invoice.company_id,
        })

    @http.route(
        '/rental/quote/accept/<int:invoice_id>',
        type='http',
        auth='public',
        website=True,
        csrf=False,
    )
    def quote_accept_public(self, invoice_id, access_token=None, **kwargs):
        """Public quote acceptance / legal terms — same access_token as invoice payment link."""

        invoice = request.env['account.move'].sudo().browse(invoice_id)

        if not invoice.exists() or invoice.move_type != 'out_invoice':
            return request.not_found()

        if not access_token or access_token != invoice.access_token:
            return request.not_found()

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
        payment_url = f"{base_url}/rental/pay/{invoice.id}?access_token={access_token}"

        deposit_amount = round(invoice.amount_total * 0.30, 2)

        # The quote_accept_public template needs sale.order fields (event_location_name,
        # order_line, setup_surface, etc.).  Look up the linked sale order so the
        # template receives the correct object regardless of which model holds the token.
        sale_orders = invoice.line_ids.mapped('sale_line_ids.order_id')
        order = sale_orders[:1]
        template_invoice = order if order else invoice

        return request.render('custom_rental.quote_accept_public', {
            'invoice': template_invoice,
            'invoice_ref': invoice.invoice_origin or invoice.name or '',
            'partner': invoice.partner_id.sudo(),
            'access_token': access_token,
            'payment_url': payment_url,
            'amount': invoice.amount_residual,
            'deposit_amount': deposit_amount,
            'currency': invoice.currency_id,
            'company': invoice.company_id,
        })

    @http.route(
        '/rental/pay/create-transaction',
        type='json',
        auth='public',
        csrf=False,
    )
    def create_payment_transaction(self, invoice_id=None, access_token=None,
                                   provider_id=None, payment_amount=None, **kwargs):
        """Create payment transaction — public route, no session needed."""
        _logger.info(
            "[Rental InvoicePay] create_payment_transaction invoice_id=%s provider_id=%s",
            invoice_id, provider_id,
        )

        if not invoice_id or not access_token or not provider_id:
            return {'error': 'Missing required parameters'}

        invoice = request.env['account.move'].sudo().browse(invoice_id)

        if not invoice.exists():
            return {'error': 'Invoice not found'}

        if access_token != invoice.access_token:
            return {'error': 'Invalid access token'}

        if invoice.payment_state in ('paid', 'in_payment'):
            return {'error': 'Invoice is already paid'}

        # Validate and resolve the charge amount
        residual = invoice.amount_residual
        if payment_amount is not None:
            try:
                payment_amount = float(payment_amount)
            except (TypeError, ValueError):
                payment_amount = residual
            # Clamp: at least 0.01, at most the full residual
            payment_amount = max(0.01, min(payment_amount, residual))
        else:
            payment_amount = residual

        provider = request.env['payment.provider'].sudo().browse(provider_id)
        if not provider.exists():
            _logger.warning("[Rental InvoicePay] provider not found provider_id=%s", provider_id)
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
            _logger.info(
                "[Rental InvoicePay] tx reference computed=%s provider_code=%s",
                reference, provider.code,
            )

            # ── Return URL after payment ──────────────────────
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
            return_url = f"{base_url}/rental/pay/status?access_token={access_token}"

            # ── Create the transaction ────────────────────────
            tx = request.env['payment.transaction'].sudo().create({
                'amount': payment_amount,
                'currency_id': invoice.currency_id.id,
                'partner_id': invoice.partner_id.id,
                'provider_id': provider_id,
                'payment_method_id': payment_method.id,
                'invoice_ids': [(6, 0, [invoice_id])],
                'reference': reference,
                'operation': 'online_redirect',
                'landing_route': return_url,
            })
            _logger.info(
                "[Rental InvoicePay] tx created id=%s reference=%s amount=%s state=%s",
                tx.id, tx.reference, tx.amount, tx.state,
            )

            client_secret = ''
            redirect_url = ''

            # ── IPOS direct flow ────────────────────────────────
            if provider.code == 'ipos_pay':
                tx.sudo().write({'operation': 'online_direct'})
                redirect_url = return_url + f'&tx_id={tx.id}'
                _logger.info(
                    "[Rental InvoicePay] ipos flow tx=%s operation=%s redirect=%s",
                    tx.id, tx.operation, redirect_url,
                )

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

            # ── Other providers (legacy) ─────────────────────
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
            _logger.error("[Rental InvoicePay] Transaction creation failed: %s", e, exc_info=True)
            return {'error': str(e)}

    # ── Quote-pay routes (order-based, no invoice until payment) ──────────────

    @http.route(
        '/rental/quote/accept_order/<int:order_id>',
        type='http',
        auth='public',
        website=True,
        csrf=False,
    )
    def quote_accept_order_public(self, order_id, access_token=None, **kwargs):
        """Terms acceptance page for a quote (order-based, no invoice yet)."""
        order = request.env['sale.order'].sudo().browse(order_id)

        if not order.exists():
            return request.not_found()
        if not access_token or access_token != order.access_token:
            return request.not_found()

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
        payment_url = f"{base_url}/rental/quote/pay/{order.id}?access_token={access_token}"
        deposit_amount = round(order.amount_total * 0.30, 2)

        return request.render('custom_rental.quote_accept_public', {
            'invoice': order,
            'invoice_ref': order.origin or '',
            'partner': order.partner_id.sudo(),
            'access_token': access_token,
            'payment_url': payment_url,
            'amount': order.amount_total,
            'deposit_amount': deposit_amount,
            'currency': order.currency_id,
            'company': order.company_id,
        })

    @http.route(
        '/rental/quote/pay/<int:order_id>',
        type='http',
        auth='public',
        website=True,
        csrf=False,
    )
    def pay_quote_public(self, order_id, access_token=None, **kwargs):
        """Payment page for a quote (order-based). Invoice created on transaction."""
        order = request.env['sale.order'].sudo().browse(order_id)

        if not order.exists():
            return request.not_found()
        if not access_token or access_token != order.access_token:
            return request.not_found()

        providers = request.env['payment.provider'].sudo().search([
            ('state', 'in', ['enabled', 'test']),
            ('company_id', 'in', [order.company_id.id, False]),
            ('code', '=', 'ipos_pay'),
        ])

        deposit_amount = round(order.amount_total * 0.30, 2)

        return request.render('custom_rental.quote_pay_public', {
            'order': order,
            'partner': order.partner_id.sudo(),
            'access_token': access_token,
            'providers': providers,
            'amount': order.amount_total,
            'deposit_amount': deposit_amount,
            'currency': order.currency_id,
            'company': order.company_id,
        })

    @http.route(
        '/rental/quote/pay/create-order-transaction',
        type='json',
        auth='public',
        csrf=False,
    )
    def create_order_payment_transaction(self, order_id=None, access_token=None,
                                         provider_id=None, payment_amount=None, **kwargs):
        """Confirm order, create full invoice, then create payment transaction for chosen amount."""
        _logger.info(
            "[Rental QuotePay] create_order_payment_transaction order_id=%s provider_id=%s amount=%s",
            order_id, provider_id, payment_amount,
        )
        if not order_id or not access_token or not provider_id:
            return {'error': 'Missing required parameters'}

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': 'Order not found'}
        if access_token != order.access_token:
            return {'error': 'Invalid access token'}
        if order.state in ('cancel',):
            return {'error': 'Order is cancelled'}

        # Resolve payment amount
        full_amount = order.amount_total
        try:
            payment_amount = float(payment_amount) if payment_amount is not None else full_amount
        except (TypeError, ValueError):
            payment_amount = full_amount
        payment_amount = max(0.01, min(payment_amount, full_amount))

        try:
            # ── 1. Confirm the order ──────────────────────────────
            if order.state in ('draft', 'sent'):
                order.action_confirm()

            # ── 2. Create a full invoice ──────────────────────────
            import secrets as _secrets
            wizard = request.env['sale.advance.payment.inv'].sudo().create({
                'advance_payment_method': 'percentage',
                'amount': 100,
                'sale_order_ids': [(6, 0, [order.id])],
            })
            wizard.with_context(active_ids=[order.id], active_model='sale.order').create_invoices()

            invoice = order.invoice_ids.filtered(lambda m: m.state == 'draft')[:1]
            if not invoice:
                return {'error': 'Invoice could not be created'}

            # Apply order-level fee lines then post
            order._apply_pos_fee_lines_to_invoice(invoice, ratio=1.0, include_tip=True)
            invoice.action_post()

            if not invoice.access_token:
                invoice.sudo().write({'access_token': _secrets.token_urlsafe(32)})

            # ── 3. Create payment transaction ────────────────────
            provider = request.env['payment.provider'].sudo().browse(provider_id)
            if not provider.exists():
                return {'error': 'Payment provider not found'}

            payment_method = request.env['payment.method'].sudo().search([
                ('provider_ids', 'in', [provider_id]),
                ('active', '=', True),
            ], limit=1)
            if not payment_method:
                return {'error': 'No payment method configured for this provider'}

            reference = request.env['payment.transaction'].sudo()._compute_reference(
                provider.code,
                prefix=invoice.name.replace('/', '-'),
            )

            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
            inv_access_token = invoice.access_token
            return_url = f"{base_url}/rental/pay/status?access_token={inv_access_token}"

            tx = request.env['payment.transaction'].sudo().create({
                'amount': payment_amount,
                'currency_id': order.currency_id.id,
                'partner_id': order.partner_id.id,
                'provider_id': provider_id,
                'payment_method_id': payment_method.id,
                'invoice_ids': [(6, 0, [invoice.id])],
                'reference': reference,
                'operation': 'online_redirect',
                'landing_route': return_url,
            })

            client_secret = ''
            redirect_url  = ''

            if provider.code == 'ipos_pay':
                tx.sudo().write({'operation': 'online_direct'})
                redirect_url = return_url + f'&tx_id={tx.id}'
            elif provider.code == 'demo':
                try:
                    tx.sudo()._set_done()
                    tx.sudo()._reconcile_after_done()
                except Exception as e:
                    _logger.warning("Demo reconcile failed: %s", e)
                redirect_url = return_url + f'&tx_id={tx.id}'
            elif provider.code == 'custom':
                try:
                    tx.sudo().write({'state': 'pending'})
                except Exception as e:
                    _logger.warning("Custom state set failed: %s", e)
                redirect_url = return_url + f'&tx_id={tx.id}'
            else:
                try:
                    processing = tx._get_processing_values()
                    redirect_url = processing.get('redirect_url', return_url + f'&tx_id={tx.id}')
                except Exception as e:
                    _logger.warning("Processing values failed: %s", e)
                    redirect_url = return_url + f'&tx_id={tx.id}'

            _logger.info(
                "[Rental QuotePay] tx=%s reference=%s amount=%s redirect=%s",
                tx.id, reference, payment_amount, redirect_url,
            )
            return {
                'tx_id': tx.id,
                'reference': reference,
                'client_secret': client_secret,
                'redirect_url': redirect_url,
                'provider_code': provider.code,
            }

        except Exception as e:
            _logger.error("[Rental QuotePay] Transaction creation failed: %s", e, exc_info=True)
            return {'error': str(e)}

    @http.route(
        '/rental/waiver/<int:order_id>',
        type='http',
        auth='public',
        website=True,
        csrf=False,
    )
    def rental_waiver(self, order_id, access_token=None, **kwargs):
        """Public waiver / liability release page — access_token validated against sale.order."""
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return request.not_found()
        if not access_token or access_token != order.access_token:
            return request.not_found()
        return request.render('custom_rental.rental_waiver_public', {
            'order': order,
            'partner': order.partner_id.sudo(),
            'company': order.company_id,
        })

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
