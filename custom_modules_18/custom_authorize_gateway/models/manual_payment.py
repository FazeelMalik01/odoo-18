from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.custom_authorize_gateway.models.authorize_request import CustomAuthorizeAPI

import logging
_logger = logging.getLogger(__name__)


class AuthorizeManualPayment(models.TransientModel):
    _name = 'authorize.manual.payment'
    _description = 'Manual Authorize Payment'

    partner_id = fields.Many2one('res.partner', required=True)
    amount = fields.Float(required=True)
    payment_date = fields.Date(default=fields.Date.today, required=True)
    journal_id = fields.Many2one('account.journal', string='Journal')
    memo = fields.Char()
    provider_id = fields.Many2one(
        'payment.provider',
        string='Payment Provider',
        domain=[('code', '=', 'authorize')],
        required=True,
    )

    opaque_data_descriptor = fields.Char()
    opaque_data_value = fields.Char()

    capture_action = fields.Selection(
        selection=[('capture', 'Capture'), ('confirm', 'Confirm')],
        string='Payment Type',
        required=True,
        default='confirm',
    )

    def action_process_payment(self):
        self.ensure_one()
        if not self.opaque_data_value:
            raise UserError(_('Card data not received. Please enter card details.'))

        # capture → auth_only (authorized state), confirm → auth_capture (done state)
        transaction_type = 'auth_only' if self.capture_action == 'capture' else 'auth_capture'

        api = CustomAuthorizeAPI(self.provider_id)
        result = api.charge_opaque_data(
            partner=self.partner_id,
            amount=self.amount,
            descriptor=self.opaque_data_descriptor,
            value=self.opaque_data_value,
            transaction_type=transaction_type,
        )

        if result.get('error'):
            raise UserError(result['error'])

        tx = self._create_payment_transaction(result)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Transaction'),
            'res_model': 'payment.transaction',
            'res_id': tx.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_payment_transaction(self, result):
        # capture → authorized state, confirm → done state
        is_capture = self.capture_action == 'capture'

        _logger.info("=== MANUAL AUTHORIZE PAYMENT ===")
        _logger.info("Provider: %s", self.provider_id.name)
        _logger.info("capture_action: %s", self.capture_action)
        _logger.info("operation will be: %s", 'validation' if is_capture else 'online_direct')
        _logger.info("result from Authorize.Net: %s", result)

        journal = self.journal_id or self.env['account.journal'].search(
            [('type', 'in', ['bank', 'cash']),
            ('company_id', '=', self.env.company.id)],
            limit=1
        )

        operation = 'validation' if is_capture else 'online_direct'

        reference = self.env['payment.transaction']._compute_reference(
            provider_code='authorize',
            prefix=self.memo or 'MANUAL',
        )

        _logger.info("Creating payment.transaction with operation=%s reference=%s", operation, reference)

        tx = self.env['payment.transaction'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.env['payment.method'].search(
                [('code', '=', 'card')], limit=1
            ).id,
            'reference': reference,
            'amount': self.amount,
            'currency_id': self.env.company.currency_id.id,
            'partner_id': self.partner_id.id,
            'operation': operation,
            'state': 'draft',
        })

        _logger.info("Transaction created: id=%s state=%s operation=%s", tx.id, tx.state, tx.operation)

        tx.provider_reference = result.get('x_trans_id', '')
        _logger.info("Set provider_reference=%s", tx.provider_reference)

        if is_capture:
            # "Capture" action → set transaction to authorized (hold funds, not yet confirmed)
            _logger.info(">>> capture branch: calling _set_authorized()")
            tx._set_authorized()
            _logger.info("After _set_authorized: tx.state=%s", tx.state)
            if not tx.payment_id:
                _logger.info("No payment_id on tx, creating draft account.payment")
                payment = self.env['account.payment'].create({
                    'partner_id': self.partner_id.id,
                    'amount': self.amount,
                    'date': self.payment_date,
                    'memo': self.memo or ('Authorize.Net TXN: %s' % result.get('x_trans_id', '')),
                    'journal_id': journal.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'currency_id': self.env.company.currency_id.id,
                })
                tx.payment_id = payment
                _logger.info("Draft payment created: %s", payment.name)
            else:
                _logger.info("payment_id already set: %s", tx.payment_id)
        else:
            # "Confirm" action → set transaction to done and post the payment
            _logger.info(">>> confirm branch: calling _set_done()")
            tx._set_done()
            _logger.info("After _set_done: tx.state=%s", tx.state)
            tx._post_process()
            _logger.info("After _post_process: tx.state=%s payment_id=%s", tx.state, tx.payment_id)
            if tx.payment_id and journal:
                tx.payment_id.write({'journal_id': journal.id})
                if tx.payment_id.state == 'draft':
                    tx.payment_id.action_post()
                _logger.info("Payment posted: %s state=%s", tx.payment_id.name, tx.payment_id.state)

        _logger.info("=== FINAL tx.state=%s tx.payment_id=%s ===", tx.state, tx.payment_id)
        return tx