# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPosAnalytic(http.Controller):
#     @http.route('/custom_pos_analytic/custom_pos_analytic', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_pos_analytic/custom_pos_analytic/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_pos_analytic.listing', {
#             'root': '/custom_pos_analytic/custom_pos_analytic',
#             'objects': http.request.env['custom_pos_analytic.custom_pos_analytic'].search([]),
#         })

#     @http.route('/custom_pos_analytic/custom_pos_analytic/objects/<model("custom_pos_analytic.custom_pos_analytic"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_pos_analytic.object', {
#             'object': obj
#         })

