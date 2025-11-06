# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class CustomBarcodeSearch(http.Controller):
    @http.route('/custom_barcode_search/search_product', type='json', auth='user', methods=['POST'])
    def search_product(self, search_term, **kwargs):
        """Search for products by barcode, packaging barcode, or name"""
        try:
            # First search by product barcode
            products = request.env['product.product'].search([('barcode', '=', search_term)])
            
            # If not found, search by packaging barcode
            if not products:
                packaging = request.env['product.packaging'].search([('barcode', '=', search_term)], limit=1)
                if packaging:
                    products = request.env['product.product'].search([('id', '=', packaging.product_id.id)])
            
            # If still not found, search by product name
            if not products:
                products = request.env['product.product'].search([
                    ('name', 'ilike', search_term)
                ]) or request.env['product.product'].search([
                    ('name', 'ilike', '%' + search_term + '%')
                ], limit=10)
            
            if not products:
                return {'success': False, 'message': f'No product found for: {search_term}'}
            
            if len(products) == 1:
                product = products[0]
                return {
                    'success': True,
                    'product': {
                        'id': product.id, 'name': product.name,
                        'barcode': product.barcode or search_term,
                        'display_name': product.display_name
                    }
                }
            else:
                return {
                    'success': True,
                    'suggestions': [{
                        'id': p.id, 'name': p.name,
                        'barcode': p.barcode or f"NO_BARCODE_{p.id}",
                        'display_name': p.display_name
                    } for p in products]
                }
        except Exception as e:
            return {'success': False, 'message': str(e)}

