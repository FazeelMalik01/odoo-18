# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPosDiscount(http.Controller):
#     @http.route('/custom_pos_discount/custom_pos_discount', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_pos_discount/custom_pos_discount/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_pos_discount.listing', {
#             'root': '/custom_pos_discount/custom_pos_discount',
#             'objects': http.request.env['custom_pos_discount.custom_pos_discount'].search([]),
#         })

#     @http.route('/custom_pos_discount/custom_pos_discount/objects/<model("custom_pos_discount.custom_pos_discount"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_pos_discount.object', {
#             'object': obj
#         })

