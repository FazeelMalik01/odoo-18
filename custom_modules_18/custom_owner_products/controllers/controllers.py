# -*- coding: utf-8 -*-
# from odoo import http


# class CustomOwnerProducts(http.Controller):
#     @http.route('/custom_owner_products/custom_owner_products', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_owner_products/custom_owner_products/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_owner_products.listing', {
#             'root': '/custom_owner_products/custom_owner_products',
#             'objects': http.request.env['custom_owner_products.custom_owner_products'].search([]),
#         })

#     @http.route('/custom_owner_products/custom_owner_products/objects/<model("custom_owner_products.custom_owner_products"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_owner_products.object', {
#             'object': obj
#         })

