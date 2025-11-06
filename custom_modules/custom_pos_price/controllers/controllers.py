# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPosPrice(http.Controller):
#     @http.route('/custom_pos_price/custom_pos_price', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_pos_price/custom_pos_price/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_pos_price.listing', {
#             'root': '/custom_pos_price/custom_pos_price',
#             'objects': http.request.env['custom_pos_price.custom_pos_price'].search([]),
#         })

#     @http.route('/custom_pos_price/custom_pos_price/objects/<model("custom_pos_price.custom_pos_price"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_pos_price.object', {
#             'object': obj
#         })

