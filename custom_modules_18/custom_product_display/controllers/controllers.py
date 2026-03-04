# -*- coding: utf-8 -*-
# from odoo import http


# class CustomProductDisplay(http.Controller):
#     @http.route('/custom_product_display/custom_product_display', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_product_display/custom_product_display/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_product_display.listing', {
#             'root': '/custom_product_display/custom_product_display',
#             'objects': http.request.env['custom_product_display.custom_product_display'].search([]),
#         })

#     @http.route('/custom_product_display/custom_product_display/objects/<model("custom_product_display.custom_product_display"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_product_display.object', {
#             'object': obj
#         })

