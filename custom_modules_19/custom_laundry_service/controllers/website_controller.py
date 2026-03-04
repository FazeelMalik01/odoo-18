# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class WebsiteController(http.Controller):

    @http.route('/pricing', type='http', auth='public', website=True, sitemap=True)
    def pricing_page(self, **kw):
        """Pricing page route"""
        # Get products with service_size = small, medium, large
        ProductTemplate = request.env['product.template'].sudo()
        
        # Fetch products by service size
        small_product = ProductTemplate.search([
            ('service_size', '=', 'small'),
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ], limit=1)
        
        medium_product = ProductTemplate.search([
            ('service_size', '=', 'medium'),
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ], limit=1)
        
        large_product = ProductTemplate.search([
            ('service_size', '=', 'large'),
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ], limit=1)
        
        # Format product data
        def format_product(product):
            if not product:
                return None
            price = product.list_price or 0.0
            return {
                'id': product.id,
                'name': product.name or 'N/A',
                'price': price,
                'price_formatted': '{:.2f}'.format(price),
                'currency': product.currency_id.symbol if product.currency_id else '$'
            }
        
        # Check if user is in customer group
        is_customer = request.env.user.has_group('custom_laundry_service.group_customer') if not request.env.user._is_public() else False
        
        values = {
            'small_product': format_product(small_product),
            'medium_product': format_product(medium_product),
            'large_product': format_product(large_product),
            'is_user_logged_in': not request.env.user._is_public(),
            'is_customer': is_customer,
        }
        
        return request.render('custom_laundry_service.pricing_page_template', values)

