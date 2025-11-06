# -*- coding: utf-8 -*-
# from odoo import http


# class CustomAnalyticFilters(http.Controller):
#     @http.route('/custom_analytic_filters/custom_analytic_filters', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_analytic_filters/custom_analytic_filters/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_analytic_filters.listing', {
#             'root': '/custom_analytic_filters/custom_analytic_filters',
#             'objects': http.request.env['custom_analytic_filters.custom_analytic_filters'].search([]),
#         })

#     @http.route('/custom_analytic_filters/custom_analytic_filters/objects/<model("custom_analytic_filters.custom_analytic_filters"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_analytic_filters.object', {
#             'object': obj
#         })

