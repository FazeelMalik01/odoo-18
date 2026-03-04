from odoo import http
from odoo.http import request
import logging


_logger = logging.getLogger(__name__)

class WebsiteSaleFlooss(http.Controller):

    @http.route(['/shop/payment/flooss_phone'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def payment_transaction_flooss_phone(self, **post):
        order = request.website.sale_get_order()
        if not order:
            _logger.warning("No active sale order found.")
            return request.not_found()

        tx = order.transaction_id
        if not tx or not tx.exists():
            _logger.warning("No active payment transaction found for order %s", order.id)
            return request.not_found()

        if tx.provider_code == 'flooss':
            flooss_phone = post.get('flooss_phone')
            if flooss_phone:
                tx.sudo().write({'flooss_verified_phone': flooss_phone})
                _logger.info("Flooss phone updated for tx %s", tx.id)

        return request.redirect('/shop/confirmation')

    
    @http.route('/get/partner/phone', type='json', auth='public', website=True)
    def get_partner_phone(self, partner_id):
        partner = request.env['res.partner'].sudo().browse(int(partner_id))
        if not partner.exists():
            return {'phone': False}
        return {'phone': partner.phone or partner.mobile or False}
        

    @http.route('/payment/flooss/current_order_contact', type='json', auth='public', website=True, methods=['POST'])
    def flooss_current_order_contact(self):
        order = request.website.sale_get_order()
        if not order:
            return {'error': 'no_order'}

        shipping = order.partner_shipping_id
        billing = order.partner_invoice_id

        return {
            'partner_shipping_id': shipping.id,
            'partner_invoice_id': billing.id,
            'shipping_phone': shipping.phone or shipping.mobile or '',
            'billing_phone': billing.phone or billing.mobile or '',
        }



