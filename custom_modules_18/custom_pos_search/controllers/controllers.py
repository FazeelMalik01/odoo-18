# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPosSearch(http.Controller):
#     @http.route('/custom_pos_search/custom_pos_search', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_pos_search/custom_pos_search/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_pos_search.listing', {
#             'root': '/custom_pos_search/custom_pos_search',
#             'objects': http.request.env['custom_pos_search.custom_pos_search'].search([]),
#         })

#     @http.route('/custom_pos_search/custom_pos_search/objects/<model("custom_pos_search.custom_pos_search"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_pos_search.object', {
#             'object': obj
#         })

