from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dealer = fields.Many2one(
        'res.partner',
        string='Dealer',
        help='Dealer who created this order from portal'
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_set_dealer_from_customer(self):
        for order in self:
            if order.partner_id:
                order.dealer = order.partner_id.dealer

    shipping_option_dropship = fields.Selection(
        [
            ('rate_quote', 'Provide a rate quote before shipping'),
            ('cheapest_rate', 'Please ship at cheapest rate'),
            ('own_carrier', 'Client will use their own carrier'),
            ('client_pickup', 'Client will pickup'),
            ('yannick_pickup', 'Yannick will pickup this order'),
            ('dhc_courier', "Ship with DHC's courier and add cost to invoice"),
        ],
        string='Shipping Option for Dropship',
        help='Shipping option preference for dropship orders'
    )

    portal_state = fields.Selection(
        [
            ('to_be_approved', 'To Be Approved'),
            ('in_progress', 'In Progress'),
            ('done', 'Sales Order'),
            ('cancelled', 'Cancelled'),
        ],
        string='Portal Status',
        default='to_be_approved',
        tracking=True,
        help='Status shown for dealer portal workflow.',
    )

    admin_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('sale', 'Sales Order'),
            ('cancel', 'Cancelled'),
        ],
        compute='_compute_admin_state',
        string='Status',
    )

    admin_submission_email_sent_at = fields.Datetime(
        string='Portal Submission Email Sent',
        readonly=True,
        copy=False,
    )
    dealer_confirm_email_sent_at = fields.Datetime(
        string='Dealer Confirmation Email Sent',
        readonly=True,
        copy=False,
    )

    def _send_email(self, email_to, subject, body_html):
        if not email_to:
            return False
        mail_values = {
            'subject': subject,
            'body_html': body_html,
            'email_to': email_to,
        }
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()
        return True

    @api.depends('state')
    def _compute_admin_state(self):
        for order in self:
            if order.state == 'cancel':
                order.admin_state = 'cancel'
            elif order.state in ('sale', 'done'):
                order.admin_state = 'sale'
            else:
                # draft/sent and any other pre-confirmation states
                order.admin_state = 'draft'

    def action_notify_admin_portal_submission(self):
        """Notify admin when a dealer submits a quotation from portal."""
        admin_email = 'team@diamondhoofcare.com'
        for order in self:
            if not order.dealer or order.admin_submission_email_sent_at:
                continue
            dealer_partner = order.dealer
            subject = f'Portal quotation submitted: {order.name}'
            body_html = (
                f'<p>A dealer submitted a quotation from the portal.</p>'
                f'<ul>'
                f'<li><strong>Order</strong>: {order.name}</li>'
                f'<li><strong>Dealer</strong>: {dealer_partner.display_name}</li>'
                f'<li><strong>Customer</strong>: {order.partner_id.display_name}</li>'
                f'<li><strong>Total</strong>: {order.amount_total} {order.currency_id.name}</li>'
                f'</ul>'
            )
            try:
                if order._send_email(admin_email, subject, body_html):
                    order.sudo().write({'admin_submission_email_sent_at': fields.Datetime.now()})
            except Exception as e:
                _logger.error("Failed to email admin for portal submission %s: %s", order.id, e, exc_info=True)

    def action_confirm(self):
        """On backoffice confirm, email the dealer once (dealer-created orders only)."""
        res = super().action_confirm()
        for order in self:
            # Keep custom portal workflow aligned with actual SO confirmation.
            if order.dealer and order.portal_state != 'done' and order.state in ('sale', 'done'):
                order.sudo().write({'portal_state': 'done'})

            if not order.dealer or order.dealer_confirm_email_sent_at:
                continue
            dealer_partner = order.dealer
            subject = f'Order confirmed: {order.name}'
            body_html = (
                f'<p>Your order has been confirmed.</p>'
                f'<ul>'
                f'<li><strong>Order</strong>: {order.name}</li>'
                f'<li><strong>Total</strong>: {order.amount_total} {order.currency_id.name}</li>'
                f'</ul>'
            )
            try:
                if order._send_email(dealer_partner.email, subject, body_html):
                    order.sudo().write({'dealer_confirm_email_sent_at': fields.Datetime.now()})
            except Exception as e:
                _logger.error("Failed to email dealer on confirm %s: %s", order.id, e, exc_info=True)
        return res

    def action_set_portal_in_progress(self):
        """Move dealer portal status from To Be Approved to In Progress."""
        for order in self:
            if not order.dealer:
                continue
            if order.portal_state != 'to_be_approved':
                continue
            # Do not confirm the quotation; only advance portal workflow state.
            order.sudo().write({'portal_state': 'in_progress'})
        return True

    def action_cancel(self):
        """Keep portal workflow status in sync when quotation/order is cancelled."""
        res = super().action_cancel()
        for order in self:
            if order.dealer and order.portal_state != 'cancelled':
                order.sudo().write({'portal_state': 'cancelled'})
        return res

    # Note: portal_state is used for portal/admin visibility only.
    # Confirmation to Sales Order should be done via the standard Confirm button.