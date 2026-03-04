# -*- coding: utf-8 -*-
# from odoo import http


# class CustomInvoiceSequence(http.Controller):
#     @http.route('/custom_invoice_sequence/custom_invoice_sequence', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_invoice_sequence/custom_invoice_sequence/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_invoice_sequence.listing', {
#             'root': '/custom_invoice_sequence/custom_invoice_sequence',
#             'objects': http.request.env['custom_invoice_sequence.custom_invoice_sequence'].search([]),
#         })

#     @http.route('/custom_invoice_sequence/custom_invoice_sequence/objects/<model("custom_invoice_sequence.custom_invoice_sequence"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_invoice_sequence.object', {
#             'object': obj
#         })

