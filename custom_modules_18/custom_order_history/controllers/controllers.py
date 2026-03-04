# -*- coding: utf-8 -*-
# from odoo import http


# class CustomOrderHistory(http.Controller):
#     @http.route('/custom_order_history/custom_order_history', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_order_history/custom_order_history/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_order_history.listing', {
#             'root': '/custom_order_history/custom_order_history',
#             'objects': http.request.env['custom_order_history.custom_order_history'].search([]),
#         })

#     @http.route('/custom_order_history/custom_order_history/objects/<model("custom_order_history.custom_order_history"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_order_history.object', {
#             'object': obj
#         })

