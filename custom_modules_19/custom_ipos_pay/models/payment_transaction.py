# -*- coding: utf-8 -*-

from odoo import models
from odoo.exceptions import ValidationError


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """Expose IPOS direct-flow values needed by the checkout frontend."""
        if self.provider_code != 'ipos_pay':
            return super()._get_specific_processing_values(processing_values)
        provider = self.provider_id.sudo()
        return {
            'ipos_security_key': (provider.ipos_auth_token or '').strip(),
            'ipos_charge_route': '/payment/ipos_pay/charge_token',
        }

    def _create_payment(self, **extra_create_values):
        """Ensure IPOS can always create account.payment with a valid method line."""
        self.ensure_one()
        if self.provider_code != 'ipos_pay':
            return super()._create_payment(**extra_create_values)

        provider = self.provider_id.sudo()
        journal = provider.journal_id
        if not journal:
            company = provider.company_id or self.company_id or self.env.company
            journal = self.env['account.journal'].sudo().search(
                [('type', '=', 'bank'), ('company_id', '=', company.id)],
                limit=1
            ) or self.env['account.journal'].sudo().search(
                [('type', 'in', ['bank', 'cash']), ('company_id', '=', company.id)],
                limit=1
            )
            if journal:
                # Persist for next transactions.
                provider.sudo().write({'journal_id': journal.id})
            else:
                raise ValidationError("IPOS Pay: No bank/cash journal found for provider company.")

        # Ensure payment is created on the resolved journal.
        if not extra_create_values.get('journal_id'):
            extra_create_values['journal_id'] = journal.id

        if not extra_create_values.get('payment_method_line_id'):
            # Preferred: manual inbound payment method line.
            method_line = journal.inbound_payment_method_line_ids.filtered(
                lambda l: l.code == 'manual'
            )[:1]
            # Fallback: provider-linked inbound method line.
            if not method_line:
                method_line = journal.inbound_payment_method_line_ids.filtered(
                    lambda l: l.payment_provider_id == provider
                )[:1]
            # Last fallback: any inbound method line.
            if not method_line:
                method_line = journal.inbound_payment_method_line_ids[:1]

            if not method_line:
                raise ValidationError(
                    "IPOS Pay: No inbound payment method line found on the provider journal."
                )
            extra_create_values['payment_method_line_id'] = method_line.id

        return super()._create_payment(**extra_create_values)
