# -*- coding: utf-8 -*-
# from odoo import http


# class CustomLabelReport(http.Controller):
#     @http.route('/custom_label_report/custom_label_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_label_report/custom_label_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_label_report.listing', {
#             'root': '/custom_label_report/custom_label_report',
#             'objects': http.request.env['custom_label_report.custom_label_report'].search([]),
#         })

#     @http.route('/custom_label_report/custom_label_report/objects/<model("custom_label_report.custom_label_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_label_report.object', {
#             'object': obj
#         })

