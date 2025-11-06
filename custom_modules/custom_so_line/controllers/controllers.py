# -*- coding: utf-8 -*-
# from odoo import http


# class CustomSoLine(http.Controller):
#     @http.route('/custom_so_line/custom_so_line', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_so_line/custom_so_line/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_so_line.listing', {
#             'root': '/custom_so_line/custom_so_line',
#             'objects': http.request.env['custom_so_line.custom_so_line'].search([]),
#         })

#     @http.route('/custom_so_line/custom_so_line/objects/<model("custom_so_line.custom_so_line"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_so_line.object', {
#             'object': obj
#         })

