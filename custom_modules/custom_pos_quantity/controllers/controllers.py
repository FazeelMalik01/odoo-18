# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPosQuantity(http.Controller):
#     @http.route('/custom_pos_quantity/custom_pos_quantity', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_pos_quantity/custom_pos_quantity/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_pos_quantity.listing', {
#             'root': '/custom_pos_quantity/custom_pos_quantity',
#             'objects': http.request.env['custom_pos_quantity.custom_pos_quantity'].search([]),
#         })

#     @http.route('/custom_pos_quantity/custom_pos_quantity/objects/<model("custom_pos_quantity.custom_pos_quantity"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_pos_quantity.object', {
#             'object': obj
#         })

