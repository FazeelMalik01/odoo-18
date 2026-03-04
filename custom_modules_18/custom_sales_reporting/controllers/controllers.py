# -*- coding: utf-8 -*-
# from odoo import http


# class CustomSalesReporting(http.Controller):
#     @http.route('/custom_sales_reporting/custom_sales_reporting', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_sales_reporting/custom_sales_reporting/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_sales_reporting.listing', {
#             'root': '/custom_sales_reporting/custom_sales_reporting',
#             'objects': http.request.env['custom_sales_reporting.custom_sales_reporting'].search([]),
#         })

#     @http.route('/custom_sales_reporting/custom_sales_reporting/objects/<model("custom_sales_reporting.custom_sales_reporting"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_sales_reporting.object', {
#             'object': obj
#         })

