# -*- coding: utf-8 -*-
# from odoo import http


# class CustomAbandonedCart(http.Controller):
#     @http.route('/custom_abandoned_cart/custom_abandoned_cart', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_abandoned_cart/custom_abandoned_cart/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_abandoned_cart.listing', {
#             'root': '/custom_abandoned_cart/custom_abandoned_cart',
#             'objects': http.request.env['custom_abandoned_cart.custom_abandoned_cart'].search([]),
#         })

#     @http.route('/custom_abandoned_cart/custom_abandoned_cart/objects/<model("custom_abandoned_cart.custom_abandoned_cart"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_abandoned_cart.object', {
#             'object': obj
#         })

