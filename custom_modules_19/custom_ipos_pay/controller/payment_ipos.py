# -*- coding: utf-8 -*-

import json
import logging
import pprint
import time

import requests

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class IposPayController(http.Controller):

    # ── Route constants ────────────────────────────────────────────────────
    _redirect_url   = '/payment/ipos_pay/redirect'
    _return_url     = '/payment/ipos_pay/return'
    _webhook_url    = '/payment/ipos_pay/webhook'

    @staticmethod
    def _get_public_base_url():
        """
        Build a public website base URL for gateway callbacks/redirects.
        Priority:
          1) current website.domain (if website module is installed/configured)
          2) web.base.url
          3) current request host_url
        Enforce https by default for externally visible callbacks.
        """
        website_domain = ''
        try:
            website = request.env['website'].sudo().get_current_website()
            website_domain = (website.domain or '').strip()
        except Exception:
            website_domain = ''

        base = website_domain or (
            request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            or request.httprequest.host_url
        )
        base = (base or '').strip().rstrip('/')
        if not base:
            return ''
        if not base.startswith(('http://', 'https://')):
            base = f"https://{base}"
        elif base.startswith('http://'):
            base = 'https://' + base[len('http://'):]
        return base

    @staticmethod
    def _post_json_with_retry(url, payload, headers, timeout=90, retries=3, backoff=1.0):
        """
        POST JSON with retries to survive transient DNS/network issues.
        Retries only on request/connection errors, not on HTTP error status.
        """
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                return requests.post(url, json=payload, headers=headers, timeout=timeout)
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                _logger.warning(
                    "IPOS Pay — request attempt %s/%s failed for %s: %s",
                    attempt, retries, url, exc,
                )
                if attempt < retries:
                    time.sleep(backoff * attempt)
        raise last_exc

    @staticmethod
    def _build_unique_transaction_reference_id(tx_sudo):
        """
        IPOS requires transactionReferenceId to be unique.
        Keep sale order number as base, append epoch-ms suffix.
        """
        base_ref = (tx_sudo.reference or '').strip()
        # Use SO number portion as base when tx references contain suffixes.
        so_ref = base_ref.split('-', 1)[0] if '-' in base_ref else base_ref
        unique_suffix = int(time.time() * 1000)
        return f"{so_ref}-{unique_suffix}", so_ref

    @staticmethod
    def _extract_card_token(payload):
        """Best-effort card token extraction from HPP/webhook payload."""
        if isinstance(payload, dict):
            for key in (
                'cardToken', 'cardtoken', 'card_token',
                'requestCardToken', 'tokenizedCard', 'tokenized_card',
            ):
                val = payload.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            for val in payload.values():
                found = IposPayController._extract_card_token(val)
                if found:
                    return found
        elif isinstance(payload, list):
            for item in payload:
                found = IposPayController._extract_card_token(item)
                if found:
                    return found
        return None

    @staticmethod
    def _ipos_get_v3_base_url(v1_base_url):
        base = (v1_base_url or '').rstrip('/')
        if '/api/v1' in base:
            return base.replace('/api/v1', '/api/v3')
        return f"{base}/api/v3"

    def _ipos_call_ipos_transact(self, tx_sudo, payment_token_id):
        """
        Call POST /api/v3/iposTransact with the FTD payment token id.
        Returns {'status': 'success'|'failure', ...}
        """
        provider = tx_sudo.provider_id
        v1_base = provider._ipos_get_base_url()
        v3_base = self._ipos_get_v3_base_url(v1_base)
        url = f"{v3_base}/iposTransact"
        merchant_id = (provider.ipos_merchant_id or '').strip()
        try:
            token = self._ipos_generate_ipostransact_token(provider)
        except ValidationError as ve:
            return {'status': 'failure', 'message': str(ve)}

        if not merchant_id or not token:
            return {'status': 'failure', 'message': 'IPOS merchant/auth configuration not valid.'}

        # Keep amount format aligned with HPP request (cents as string).
        amount_cents = str(int(tx_sudo.amount * 100))
        # IPOS requires globally unique transactionReferenceId per attempt.
        # Keep Odoo internal reference unchanged; only vary the provider payload reference.
        unique_reference, _base_ref = self._build_unique_transaction_reference_id(tx_sudo)

        payload = {
            'merchantAuthentication': {
                'merchantId': merchant_id,
                'transactionReferenceId': unique_reference,
            },
            'transactionRequest': {
                'transactionType': 1,
                'amount': amount_cents,
                # FTD returns payment_token_id (single-use), not reusable cardToken.
                'paymentTokenId': payment_token_id,
                'applySteamSettingTipFeeTax': False,
            },
            'preferences': {
                'eReceipt': False,
                'requestCardToken': False,
            },
        }
        headers = {
            'token': token,
            'Content-Type': 'application/json',
        }

        _logger.info("IPOS Pay — iposTransact request | url=%s | payload=%s", url, pprint.pformat(payload))
        try:
            resp = self._post_json_with_retry(url, payload, headers, timeout=90, retries=3, backoff=1.0)
            if not resp.ok:
                return {'status': 'failure', 'message': self._ipos_http_error_detail(resp)}
            try:
                body = resp.json()
            except ValueError:
                return {'status': 'failure', 'message': 'Invalid JSON from iposTransact.'}
        except Exception as e:
            return {'status': 'failure', 'message': str(e)}

        _logger.info("IPOS Pay — iposTransact response: %s", pprint.pformat(body))
        # iPOS commonly nests transaction details under `iposhpresponse`.
        tx_body = body.get('iposhpresponse') if isinstance(body, dict) else None
        tx_body = tx_body if isinstance(tx_body, dict) else body

        response_code = str(
            tx_body.get('responseCode')
            or tx_body.get('hostResponseCode')
            or tx_body.get('errResponseCode')
            or ''
        )
        success_codes = {'200', '00', '0'}
        if response_code in success_codes:
            return {
                'status': 'success',
                'body': body,
                'provider_reference': tx_body.get('transactionId') or tx_body.get('referenceId') or '',
            }
        return {
            'status': 'failure',
            'message': (
                tx_body.get('errResponseMessage')
                or tx_body.get('hostResponseMessage')
                or tx_body.get('responseMessage')
                or 'iposTransact failed.'
            ),
            'body': body,
        }

    @http.route('/payment/ipos_pay/get_config', type='json', auth='public', csrf=False)
    def ipos_get_config(self, provider_id=None, **kwargs):
        """
        Return FTD configuration for the given IPOS Pay provider.

        FTD (freedomtodesign.js) reads two data-attributes from <script id="myScript">:
          - data-token : the auth JWT  → sent as 'token' header to /api/v1/paymentCardToken
          - data-src   : the API origin → FTD calls {data-src}/api/v1/paymentCardToken
        """
        if not provider_id:
            return {}
        provider = request.env['payment.provider'].sudo().browse(int(provider_id))
        if not provider.exists() or provider.code != 'ipos_pay' or provider.state == 'disabled':
            return {}

        from urllib.parse import urlparse
        base_url = (provider._ipos_get_base_url() or '').strip().rstrip('/')
        parsed = urlparse(base_url)
        # Origin only — FTD appends /api/v1/paymentCardToken itself.
        data_src = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else base_url

        return {
            'data_token': (provider.ipos_auth_token or '').strip(),
            'data_src': data_src,
            # FTD script lives at {origin}/ftd/v1/freedomtodesign.js
            'ftd_src': f"{data_src}/ftd/v1/freedomtodesign.js",
        }

    @staticmethod
    def _ipos_finalize_done_transaction(tx_sudo):
        """Run Odoo standard post-processing to confirm SO/invoices/payments."""
        try:
            tx_sudo._post_process()
        except Exception:
            _logger.exception(
                "IPOS Pay — post_process failed for tx=%s (state=%s)",
                tx_sudo.reference, tx_sudo.state
            )
        # Ensure customer payment is validated and invoice is reconciled/paid.
        try:
            payment = tx_sudo.payment_id
            if not payment:
                tx_sudo.with_company(tx_sudo.company_id)._create_payment()
                payment = tx_sudo.payment_id

            if payment and payment.state == 'draft':
                payment.action_post()

            invoices = tx_sudo.invoice_ids.filtered(lambda inv: inv.state != 'cancel')
            if payment and invoices:
                lines = (payment.move_id.line_ids + invoices.line_ids).filtered(
                    lambda line: line.account_id == payment.destination_account_id and not line.reconciled
                )
                if lines:
                    lines.reconcile()
        except Exception:
            _logger.exception(
                "IPOS Pay — ensure validated/paid failed for tx=%s",
                tx_sudo.reference
            )

    @http.route('/payment/ipos_pay/charge_token', type='json', auth='public', csrf=False)
    def ipos_pay_charge_token(self, reference=None, payment_token_id=None, access_token=None, **kwargs):
        """
        Direct website flow:
          1) FTD in browser generates `payment_token_id`
          2) This endpoint calls iposTransact and finalizes Odoo transaction
        """
        if not reference:
            return {'state': 'error', 'message': 'Missing transaction reference.'}
        if not payment_token_id:
            return {'state': 'error', 'message': 'Missing payment token id.'}

        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)], limit=1)
        if not tx_sudo:
            return {'state': 'error', 'message': 'Transaction not found.'}
        if tx_sudo.provider_code != 'ipos_pay':
            return {'state': 'error', 'message': 'Transaction provider mismatch.'}

        # Avoid double-processing successful transactions.
        if tx_sudo.state == 'done':
            if not tx_sudo.is_post_processed:
                self._ipos_finalize_done_transaction(tx_sudo)
            return {'state': 'done', 'landing_route': '/shop/payment/validate'}

        result = self._ipos_call_ipos_transact(tx_sudo, payment_token_id)
        if result.get('status') == 'success':
            provider_ref = result.get('provider_reference')
            if provider_ref:
                tx_sudo.write({'provider_reference': provider_ref})
            tx_sudo._set_done()
            self._ipos_finalize_done_transaction(tx_sudo)
            tx_sudo._log_message_on_linked_documents(
                _("IPOS Pay direct flow completed via FTD tokenization.\nReference: %(ref)s", ref=tx_sudo.reference)
            )
            return {'state': 'done', 'landing_route': '/shop/payment/validate'}

        tx_sudo._set_error(result.get('message') or _('IPOS direct transaction failed.'))
        return {'state': 'error', 'message': result.get('message') or 'IPOS direct transaction failed.'}

    @staticmethod
    def _ipos_http_error_detail(response):
        """Best-effort message from a failed IPOS HTTP response (for logs and ValidationError)."""
        text = (response.text or '').strip()
        if not text:
            return response.reason or str(response.status_code)
        try:
            data = response.json()
        except ValueError:
            return text[:2000]
        if not isinstance(data, dict):
            return str(data)[:2000]
        err = data.get('error') or data.get('message') or data.get('responseMessage')
        if err:
            return str(err)
        errs = data.get('errors')
        if isinstance(errs, list) and errs:
            first = errs[0]
            if isinstance(first, dict):
                return str(first.get('message') or first.get('field') or first)
            return str(first)
        return pprint.pformat(data)[:2000]

    def _ipos_token_from_provider(self, provider):
        token = (provider.sudo().ipos_auth_token or '').strip()
        if not token:
            raise ValidationError(_("IPOS Pay: Missing Auth Token on the payment provider configuration."))
        return token

    @staticmethod
    def _ipos_extract_auth_token(payload):
        """Extract auth token from authenticate-token response payload."""
        if not isinstance(payload, dict):
            return ''

        direct_keys = ('token', 'authToken', 'accessToken', 'jwt', 'jwtToken')
        for key in direct_keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        nested_keys = ('data', 'result', 'response', 'information')
        for key in nested_keys:
            nested = payload.get(key)
            if isinstance(nested, dict):
                token = IposPayController._ipos_extract_auth_token(nested)
                if token:
                    return token
        return ''

    def _ipos_generate_ipostransact_token(self, provider):
        """Generate auth token for iposTransact via authenticate-token API."""
        api_key = (provider.sudo().ipos_transact_api_key or '').strip()
        secret_key = (provider.sudo().ipos_transact_secret_key or '').strip()
        scope = (provider.ipos_transact_scope or '').strip() or 'PaymentTokenization'
        auth_url = (provider.ipos_transact_auth_url or '').strip()

        if not api_key or not secret_key or not auth_url:
            raise ValidationError(
                _("IPOS Pay: Missing iposTransact auth configuration (API Key / Secret Key / Auth URL).")
            )

        headers = {
            'apiKey': api_key,
            'secretKey': secret_key,
            'scope': scope,
            'Content-Type': 'application/json',
        }
        try:
            # Postman sample uses empty body for this endpoint.
            resp = requests.post(auth_url, headers=headers, data='', timeout=60)
            if not resp.ok:
                raise ValidationError(
                    _("IPOS Pay authenticate-token failed: %(msg)s", msg=self._ipos_http_error_detail(resp))
                )
            try:
                body = resp.json()
            except ValueError:
                raise ValidationError(_("IPOS Pay authenticate-token returned invalid JSON."))
        except requests.exceptions.RequestException as exc:
            raise ValidationError(_("IPOS Pay authenticate-token request failed: %(msg)s", msg=str(exc)))

        token = self._ipos_extract_auth_token(body)
        if not token:
            raise ValidationError(
                _("IPOS Pay authenticate-token response did not contain a usable token.")
            )
        return token

    # ══════════════════════════════════════════════════════════════════════
    # 4.  Legacy HPP routes (disabled)
    # ══════════════════════════════════════════════════════════════════════

    @http.route(_redirect_url, type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def ipos_pay_redirect(self, **post):
        _logger.warning("IPOS Pay — legacy HPP redirect route called, but HPP flow is disabled.")
        return request.redirect('/payment/status')

    # ── Internal: POST to /external-payment-transaction (HPP) ─────────────

    @staticmethod
    def _looks_like_url(value):
        return isinstance(value, str) and (value.startswith('http://') or value.startswith('https://'))

    @staticmethod
    def _extract_first_url(obj):
        """Fallback: find the first http(s) URL anywhere in a JSON-like payload."""
        if IposPayController._looks_like_url(obj):
            return obj
        if isinstance(obj, dict):
            for v in obj.values():
                found = IposPayController._extract_first_url(v)
                if found:
                    return found
            return None
        if isinstance(obj, list):
            for v in obj:
                found = IposPayController._extract_first_url(v)
                if found:
                    return found
            return None
        return None

    def _ipos_create_external_payment_transaction(self, provider, tx_sudo, tpn):
        """
        POST {base_url}/external-payment-transaction
        Returns { status, checkout_url } or { status, message }.
        """
        base_url = (provider._ipos_get_base_url() or '').rstrip('/')
        primary_url = f"{base_url}/external-payment-transaction"

        # Use public website URL (HTTPS) for gateway callbacks.
        site_url = self._get_public_base_url()
        if not site_url:
            site_url = request.httprequest.host_url.rstrip('/')
        amount_cents = int(tx_sudo.amount * 100)

        reference_id, sale_order_ref = self._build_unique_transaction_reference_id(tx_sudo)

        mobile = ''.join(ch for ch in (tx_sudo.partner_phone or '') if ch.isdigit() or ch == '+')

        payload = {
            'merchantAuthentication': {
                'merchantId':             int(tpn) if tpn.isdigit() else tpn,
                'transactionReferenceId': reference_id,
            },
            'transactionRequest': {
                'transactionType':    1,
                'amount':             str(amount_cents),
                'calculateFee':       True,
                'tipsInputPrompt':    False,
                'calculateTax':       "true",
            },
            'preferences': {
                'integrationType':   1,  # HPP
                'avsVerification':   False,
                'eReceipt':          False,
                'eReceiptInputPrompt': False,
                'customerName':      tx_sudo.partner_name or '',
                'customerEmail':     tx_sudo.partner_email or '',
                'customerMobile':    mobile,
                'requestCardToken':  True,
            },
            'notificationOption': {
                'notifyBySMS':      False,
                'mobileNumber':     mobile,
                'notifyByPOST':     False,
                'notifyByRedirect': True,
                'returnUrl':        f"{site_url}{self._return_url}",
                'expiry':           5,
            },
            'txReferenceTag1': {
                'tagLabel': 'InvoiceNumber',
                'tagValue': sale_order_ref or (tx_sudo.reference or ''),
                'isTagMandate': False,
            },
            'personalization': {
                'merchantName': provider.company_id.name or 'Freedom Fun USA',
                'themeColor': '#875A7B',
                'description': 'Please complete your payment securely.',
                'payNowButtonText': 'Pay Now',
                'buttonColor': '#28A745',
                'cancelButtonText': 'Cancel',
                'disclaimer': 'All transactions are secure and encrypted. By proceeding, you agree to our terms.',
            },
        }

        headers = provider._ipos_get_api_headers()
        headers['token'] = self._ipos_token_from_provider(provider)

        _logger.info(
            "IPOS Pay — external-payment-transaction request | url=%s | payload=%s",
            primary_url, pprint.pformat(payload)
        )

        try:
            resp = self._post_json_with_retry(primary_url, payload, headers, timeout=90, retries=3, backoff=1.0)
            if not resp.ok:
                return {'status': 'failure', 'message': self._ipos_http_error_detail(resp)}
            try:
                body = resp.json()
            except ValueError:
                return {'status': 'failure', 'message': 'Invalid JSON response from IPOS.'}
        except requests.exceptions.RequestException as e:
            _logger.error("IPOS Pay — external-payment-transaction HTTP error (%s): %s", primary_url, e)
            return {'status': 'failure', 'message': str(e)}

        _logger.info("IPOS Pay — external-payment-transaction response: %s", pprint.pformat(body))

        # Per iPOS HPP docs, hosted payment URL is returned in `information`.
        info_url = body.get('information') if isinstance(body, dict) else None
        if self._looks_like_url(info_url):
            return {'status': 'success', 'checkout_url': info_url}

        # Fallback for unexpected payload shapes (avoid false positives like logoUrl/returnUrl)
        checkout_url = self._extract_first_url(body)
        if checkout_url and 'externalPay' in checkout_url:
            return {'status': 'success', 'checkout_url': checkout_url}

        return {'status': 'failure', 'message': 'No hosted payment URL returned by IPOS.'}

    # ══════════════════════════════════════════════════════════════════════
    # 5.  RETURN URL — customer comes back from HPP page
    # ══════════════════════════════════════════════════════════════════════

    @http.route(_return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False, save_session=False)
    def ipos_pay_return(self, **data):
        """
        Customer is redirected back here after paying on the HPP page.
        iPOSpays also sends data as query params or POST body.
        We rely on the webhook for the authoritative status update,
        so here we just show the payment status page.
        """
        _logger.info("IPOS Pay — /return called with: %s", pprint.pformat(data))
        # Follow Odoo website_sale default finalization path:
        # /shop/payment/validate will route to /shop/confirmation when order is finalized.
        return request.redirect('/shop/payment/validate')

    # ══════════════════════════════════════════════════════════════════════
    # 6.  WEBHOOK — iPOSpays POSTs the final payment result here
    # ══════════════════════════════════════════════════════════════════════

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def ipos_pay_webhook(self, **kwargs):
        """
        iPOSpays calls this endpoint after a payment is processed.

        Headers : authHeader (webhookToken) for verification
        Body    : JSON with transaction result

        Flow:
          1. Parse raw JSON body
          2. Verify webhook token (authHeader)
          3. Find matching transaction by referenceId
          4. Mark transaction paid / failed
        """
        raw_data = request.httprequest.get_data(as_text=True)
        _logger.info("IPOS Pay — /webhook raw payload: %s", raw_data)

        # ── Parse JSON body ────────────────────────────────────────────
        try:
            notification = json.loads(raw_data)
        except json.JSONDecodeError:
            _logger.error("IPOS Pay — webhook received invalid JSON")
            return request.make_response('Bad Request', status=400)

        _logger.info("IPOS Pay — /webhook parsed: %s", pprint.pformat(notification))

        # ── Extract reference from payload ─────────────────────────────
        # iPOSpays sends transactionReferenceId in the format:
        #   TPNID{tpn}ORDERID{reference}
        reference_id = (
            notification.get('transactionReferenceId')
            or notification.get('merchantAuthentication', {}).get('transactionReferenceId')
            or ''
        )

        if not reference_id:
            _logger.error("IPOS Pay — webhook missing transactionReferenceId")
            return request.make_response('Missing reference', status=400)

        # ── Find transaction ───────────────────────────────────────────
        tx_sudo = request.env['payment.transaction'].sudo().search(
            [('reference', 'in', self._extract_possible_references(reference_id))],
            limit=1
        )

        if not tx_sudo:
            _logger.error("IPOS Pay — webhook: no transaction found for referenceId=%s", reference_id)
            return request.make_response('Transaction not found', status=404)

        # ── Verify webhook token ───────────────────────────────────────
        received_token = request.httprequest.headers.get('authHeader') or \
                         request.httprequest.headers.get('Authorization') or ''

        # Token stored on transaction or provider — compare securely
        # (In production: store webhookToken on the transaction or provider)
        # Here we just log it; add your token comparison logic below:
        _logger.info("IPOS Pay — webhook authHeader received: %s", received_token[:10] + '...' if received_token else 'MISSING')

        # ── Process payment result ─────────────────────────────────────
        try:
            self._ipos_process_notification(tx_sudo, notification)
        except Exception as e:
            _logger.exception("IPOS Pay — webhook processing error: %s", e)
            return request.make_response('Processing error', status=500)

        return request.make_response('OK', status=200)

    # ── Internal: extract Odoo reference from IPOS composite referenceId ──

    def _extract_possible_references(self, reference_id):
        """
        IPOS reference format: TPNID{tpn}ORDERID{odoo_reference}UNIQUEID{uuid}
        Extract the Odoo transaction reference from the composite string.
        Returns a list of possible references to search for.
        """
        references = [reference_id]  # always try full string first

        # Try to extract the portion between ORDERID and UNIQUEID
        if 'ORDERID' in reference_id:
            after_order = reference_id.split('ORDERID', 1)[1]
            # Strip trailing UNIQUEID suffix if present
            if 'UNIQUEID' in after_order:
                odoo_ref = after_order.split('UNIQUEID', 1)[0]
            else:
                odoo_ref = after_order
            if odoo_ref:
                references.append(odoo_ref)

        # For new format "S00040-<epoch_ms>", also try the SO base part.
        if '-' in reference_id:
            references.append(reference_id.split('-', 1)[0])

        # De-duplicate while preserving order.
        deduped = []
        for ref in references:
            if ref and ref not in deduped:
                deduped.append(ref)
        return deduped

    # ── Internal: update transaction state from webhook data ──────────────

    def _ipos_process_notification(self, tx_sudo, notification):
        """
        Read the iPOSpays webhook payload and update the Odoo transaction.

        iPOSpays webhook payload contains the payment result in the
        same structure as the iposTransact response.
        """
        payment_info = notification.get('iposhpresponse', notification)
        card_token = self._extract_card_token(payment_info)

        response_code = (
            payment_info.get('responseCode')
            or payment_info.get('hostResponseCode')
            or ''
        )

        transaction_id  = payment_info.get('transactionId', '')
        approval_code   = payment_info.get('responseApprovalCode', '')
        rrn             = payment_info.get('rrn', '')
        total_amount    = payment_info.get('totalAmount', payment_info.get('amount', ''))
        error_message   = payment_info.get('errResponseMessage', '')

        _logger.info(
            "IPOS Pay — processing notification | responseCode=%s | transactionId=%s",
            response_code, transaction_id
        )

        # Store IPOS transaction details on the Odoo transaction
        tx_sudo.write({
            'provider_reference': transaction_id or tx_sudo.provider_reference,
        })

        # ── If HPP returned card token, process charge via iposTransact ─
        if card_token:
            _logger.info("IPOS Pay — card token found from HPP webhook; calling iposTransact.")
            transact = self._ipos_call_ipos_transact(tx_sudo, card_token)
            if transact.get('status') == 'success':
                provider_ref = transact.get('provider_reference')
                if provider_ref:
                    tx_sudo.write({'provider_reference': provider_ref})
                tx_sudo._set_done()
                self._ipos_finalize_done_transaction(tx_sudo)
                tx_sudo._log_message_on_linked_documents(
                    _("IPOS Pay tokenized flow completed via iposTransact.\nReference: %(ref)s", ref=tx_sudo.reference)
                )
                return
            tx_sudo._set_error(
                _("IPOS Pay iposTransact failed after tokenization: %(msg)s", msg=transact.get('message', _('Unknown error')))
            )
            return

        # ── Determine success or failure (fallback: direct HPP result) ─
        # iPOSpays uses '200' for embedded and '00' for some responses
        success_codes = {'200', '00', '0'}

        if response_code in success_codes:
            _logger.info(
                "IPOS Pay — payment SUCCESS | tx=%s | transactionId=%s | approval=%s",
                tx_sudo.reference, transaction_id, approval_code
            )
            tx_sudo._set_done()
            self._ipos_finalize_done_transaction(tx_sudo)

            # Optionally log extra details in the chatter
            tx_sudo._log_message_on_linked_documents(
                _(
                    "IPOS Pay payment confirmed.\n"
                    "Transaction ID : %(txn_id)s\n"
                    "Approval Code  : %(approval)s\n"
                    "RRN            : %(rrn)s\n"
                    "Amount         : %(amount)s",
                    txn_id=transaction_id,
                    approval=approval_code,
                    rrn=rrn,
                    amount=total_amount,
                )
            )
        else:
            _logger.warning(
                "IPOS Pay — payment FAILED | tx=%s | code=%s | message=%s",
                tx_sudo.reference, response_code, error_message
            )
            tx_sudo._set_error(
                _(
                    "IPOS Pay payment failed (code: %(code)s): %(msg)s",
                    code=response_code,
                    msg=error_message or _('Unknown error'),
                )
            )