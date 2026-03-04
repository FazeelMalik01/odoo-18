# -*- coding: utf-8 -*-
# from odoo import http


# class CustomCostAdjustment(http.Controller):
#     @http.route('/custom_cost_adjustment/custom_cost_adjustment', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_cost_adjustment/custom_cost_adjustment/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_cost_adjustment.listing', {
#             'root': '/custom_cost_adjustment/custom_cost_adjustment',
#             'objects': http.request.env['custom_cost_adjustment.custom_cost_adjustment'].search([]),
#         })

#     @http.route('/custom_cost_adjustment/custom_cost_adjustment/objects/<model("custom_cost_adjustment.custom_cost_adjustment"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_cost_adjustment.object', {
#             'object': obj
#         })

