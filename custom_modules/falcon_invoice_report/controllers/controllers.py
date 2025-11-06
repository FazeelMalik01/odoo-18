# -*- coding: utf-8 -*-
# from odoo import http


# class FalconInvoiceReport(http.Controller):
#     @http.route('/falcon_invoice_report/falcon_invoice_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/falcon_invoice_report/falcon_invoice_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('falcon_invoice_report.listing', {
#             'root': '/falcon_invoice_report/falcon_invoice_report',
#             'objects': http.request.env['falcon_invoice_report.falcon_invoice_report'].search([]),
#         })

#     @http.route('/falcon_invoice_report/falcon_invoice_report/objects/<model("falcon_invoice_report.falcon_invoice_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('falcon_invoice_report.object', {
#             'object': obj
#         })

