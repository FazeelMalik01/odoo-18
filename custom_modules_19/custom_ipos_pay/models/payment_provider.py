# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

_IPOS_MODULE_NAME = 'custom_ipos_pay'
_IPOS_INLINE_FORM_XMLID = 'custom_ipos_pay.ipos_pay_inline_form'
# When user's default company != active (header) company, assign provider to this company id.
_IPOS_MISMATCH_FALLBACK_COMPANY_ID = 1


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('ipos_pay', 'IPOS Pay')],
        ondelete={'ipos_pay': 'set default'},
    )

    # ── IPOS Pay Credential Fields (FTD + iposTransact) ───────────────────

    ipos_merchant_id = fields.Char(
        string='Merchant ID (TPN)',
        help='Your IPOS Pay Merchant ID / Terminal Provider Number (TPN).',
    )
    ipos_auth_token = fields.Char(
        string='Auth Token',
        help="Paste the IPOS JWT token used as the 'token' HTTP header.",
        groups='base.group_system',
    )
    ipos_transact_api_key = fields.Char(
        string='iposTransact API Key',
        help='API key used to generate PaymentTokenization token for iposTransact.',
        groups='base.group_system',
    )
    ipos_transact_secret_key = fields.Char(
        string='iposTransact Secret Key',
        help='Secret key used to generate PaymentTokenization token for iposTransact.',
        groups='base.group_system',
    )
    ipos_transact_scope = fields.Char(
        string='iposTransact Scope',
        default='PaymentTokenization',
        help='Scope header for authenticate-token API (usually PaymentTokenization).',
    )
    ipos_transact_auth_url = fields.Char(
        string='iposTransact Auth URL',
        default='https://auth.ipospays.tech/v1/authenticate-token',
        help='Token generation endpoint for iposTransact.',
    )

    # ── URL Configuration ──────────────────────────────────────────────────

    ipos_test_base_url = fields.Char(
        string='Test Base URL',
        default='https://payment.ipospays.tech/api/v1',
        help='Base URL for the IPOS Pay sandbox / test environment.',
    )
    ipos_live_base_url = fields.Char(
        string='Live Base URL',
        default='https://payment.ipospays.com/api/v1',
        help='Base URL for the IPOS Pay production / live environment.',
    )

    # ── Computed Effective URL ─────────────────────────────────────────────

    ipos_base_url = fields.Char(
        string='Effective Base URL',
        compute='_compute_ipos_base_url',
        store=False,
        help='The base URL that will be used for API calls (test or live).',
    )

    # ─────────────────────────────────────────────────────────────────────
    # Compute
    # ─────────────────────────────────────────────────────────────────────

    @api.model
    def _ipos_ensure_module_link_all(self):
        """Bind module + default payment methods for all IPOS Pay providers."""
        providers = self.search([('code', '=', 'ipos_pay')])
        providers._ipos_ensure_module_link()
        providers._ipos_ensure_payment_methods()
        providers._ipos_ensure_inline_form_view()
        return providers

    @api.model
    def _ipos_get_sync_company_id(self):
        """Align provider company with user default vs active company rule.

        - If ``user.company_id`` (default company) equals ``env.company`` (selected
          company in session), use that company.
        - Otherwise use company id ``_IPOS_MISMATCH_FALLBACK_COMPANY_ID`` (usually 1).
        Portal users: no automatic company (returns False).
        """
        user = self.env.user
        if user.share:
            return False
        default_co = user.company_id
        active_co = self.env.company
        fallback = self.env['res.company'].sudo().browse(_IPOS_MISMATCH_FALLBACK_COMPANY_ID)
        fallback_id = fallback.id if fallback.exists() else False
        if not fallback_id:
            main = self.env.ref('base.main_company', raise_if_not_found=False)
            fallback_id = main.id if main else False
        if default_co and active_co and default_co.id == active_co.id:
            return default_co.id
        return fallback_id

    def _ipos_sync_company_from_user_context(self):
        """Set ``company_id`` on IPOS providers from session/default company rule."""
        self = self.filtered(lambda p: p.code == 'ipos_pay')
        if not self or self.env.context.get('ipos_skip_sync_company'):
            return
        if self.env.user.share:
            return
        target_id = self.env['payment.provider']._ipos_get_sync_company_id()
        if not target_id:
            return
        need = self.filtered(
            lambda p: (not p.company_id) or p.company_id.id != target_id
        )
        if need:
            need.with_context(ipos_skip_sync_company=True).sudo().write(
                {'company_id': target_id}
            )

    def _ipos_ensure_module_link(self):
        self = self.filtered(lambda p: p.code == 'ipos_pay')
        if not self or self.env.context.get('ipos_skip_module_link'):
            return
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', _IPOS_MODULE_NAME)], limit=1
        )
        if not module:
            return
        to_fix = self.filtered(lambda p: p.module_id != module)
        if to_fix:
            to_fix.with_context(ipos_skip_module_link=True).sudo().write(
                {'module_id': module.id}
            )

    def _ipos_ensure_payment_methods(self):
        self = self.filtered(lambda p: p.code == 'ipos_pay')
        if not self or self.env.context.get('ipos_skip_payment_methods'):
            return
        card = self.env.ref('payment.payment_method_card', raise_if_not_found=False)
        if not card:
            return
        need = self.filtered(lambda p: card not in p.payment_method_ids)
        if need:
            need.with_context(ipos_skip_payment_methods=True).sudo().write(
                {'payment_method_ids': [(4, card.id)]}
            )

    def _ipos_ensure_journal(self):
        """Ensure a journal is set so account.payment can be created on done tx."""
        self = self.filtered(lambda p: p.code == 'ipos_pay')
        if not self or self.env.context.get('ipos_skip_journal'):
            return
        for provider in self:
            if provider.journal_id:
                continue
            company = provider.company_id or self.env.company
            journal = self.env['account.journal'].sudo().search(
                [('type', '=', 'bank'), ('company_id', '=', company.id)],
                limit=1
            ) or self.env['account.journal'].sudo().search(
                [('type', 'in', ['bank', 'cash']), ('company_id', '=', company.id)],
                limit=1
            )
            if journal:
                provider.with_context(ipos_skip_journal=True).sudo().write({'journal_id': journal.id})

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.share:
            sync_cid = self._ipos_get_sync_company_id()
            if sync_cid:
                for vals in vals_list:
                    if vals.get('code') == 'ipos_pay':
                        vals.setdefault('company_id', sync_cid)
        records = super().create(vals_list)
        records._ipos_ensure_module_link()
        records._ipos_ensure_payment_methods()
        records._ipos_ensure_inline_form_view()
        records._ipos_ensure_journal()
        return records

    def read(self, fields=None, load='_classic_read'):
        """Refresh ``company_id`` when internal user loads IPOS provider (e.g. after company switch)."""
        ipos = self.filtered(lambda p: p.code == 'ipos_pay')
        if ipos and not self.env.context.get('ipos_skip_sync_company'):
            ipos._ipos_sync_company_from_user_context()
        return super().read(fields=fields, load=load)

    def write(self, vals):
        res = super().write(vals)
        self._ipos_ensure_module_link()
        self._ipos_ensure_payment_methods()
        self._ipos_ensure_inline_form_view()
        # If provider enabled / company changed, ensure a journal exists.
        self._ipos_ensure_journal()
        if not self.env.context.get('ipos_skip_sync_company'):
            self.filtered(lambda p: p.code == 'ipos_pay')._ipos_sync_company_from_user_context()
        return res

    @api.depends('state', 'ipos_test_base_url', 'ipos_live_base_url')
    def _compute_ipos_base_url(self):
        for provider in self:
            if provider.code == 'ipos_pay':
                if provider.state == 'test':
                    provider.ipos_base_url = provider.ipos_test_base_url or ''
                else:
                    provider.ipos_base_url = provider.ipos_live_base_url or ''
            else:
                provider.ipos_base_url = ''

    # ─────────────────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────────────────

    @api.constrains(
        'code', 'ipos_merchant_id', 'ipos_auth_token',
        'ipos_transact_api_key', 'ipos_transact_secret_key', 'ipos_transact_scope', 'ipos_transact_auth_url'
    )
    def _check_ipos_required_fields(self):
        for provider in self:
            if provider.code == 'ipos_pay' and provider.state != 'disabled':
                if not (provider.ipos_merchant_id or '').strip():
                    raise ValidationError(
                        _('IPOS Pay: A Merchant ID (TPN) is required when the provider is enabled.')
                    )
                if not (provider.sudo().ipos_auth_token or '').strip():
                    raise ValidationError(
                        _('IPOS Pay: An Auth Token is required when the provider is enabled.')
                    )
                if not (provider.sudo().ipos_transact_api_key or '').strip():
                    raise ValidationError(
                        _('IPOS Pay: iposTransact API Key is required when the provider is enabled.')
                    )
                if not (provider.sudo().ipos_transact_secret_key or '').strip():
                    raise ValidationError(
                        _('IPOS Pay: iposTransact Secret Key is required when the provider is enabled.')
                    )
                if not (provider.ipos_transact_scope or '').strip():
                    raise ValidationError(
                        _('IPOS Pay: iposTransact Scope is required when the provider is enabled.')
                    )
                if not (provider.ipos_transact_auth_url or '').strip():
                    raise ValidationError(
                        _('IPOS Pay: iposTransact Auth URL is required when the provider is enabled.')
                    )

    # ─────────────────────────────────────────────────────────────────────
    # Business / Helper Methods
    # ─────────────────────────────────────────────────────────────────────

    def _ipos_get_base_url(self):
        """Return the correct base URL based on provider state."""
        self.ensure_one()
        if self.state == 'test':
            return self.ipos_test_base_url or ''
        return self.ipos_live_base_url or ''

    def _ipos_get_api_headers(self):
        """Build the HTTP headers used for IPOS API requests."""
        self.ensure_one()
        return {
            'Content-Type': 'application/json',
            'token': (self.sudo().ipos_auth_token or '').strip(),
        }

    def _get_default_payment_method_codes(self):
        """Return default payment method codes for IPOS Pay."""
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'ipos_pay':
            return default_codes
        # Extend this list as IPOS Pay supports more methods:
        # 'card', 'google_pay', 'apple_pay', 'ach'
        return {'card'}

    def _ipos_ensure_inline_form_view(self):
        self = self.filtered(lambda p: p.code == 'ipos_pay')
        if not self or self.env.context.get('ipos_skip_inline_view'):
            return
        view = self.env.ref(_IPOS_INLINE_FORM_XMLID, raise_if_not_found=False)
        if not view:
            return
        need = self.filtered(lambda p: p.inline_form_view_id != view)
        if need:
            need.with_context(ipos_skip_inline_view=True).sudo().write(
                {'inline_form_view_id': view.id}
            )

    # ─────────────────────────────────────────────────────────────────────
    # Inline Form Override
    # ─────────────────────────────────────────────────────────────────────

    def _should_build_inline_form(self, is_validation=False):
        """IPOS Pay uses direct card tokenization (FTD inline fields)."""
        if self.code == 'ipos_pay':
            return True
        return super()._should_build_inline_form(is_validation=is_validation)