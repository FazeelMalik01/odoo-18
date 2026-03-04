# -*- coding: utf-8 -*-
# from odoo import http


# class CustomGeneralLedger(http.Controller):
#     @http.route('/custom_general_ledger/custom_general_ledger', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_general_ledger/custom_general_ledger/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_general_ledger.listing', {
#             'root': '/custom_general_ledger/custom_general_ledger',
#             'objects': http.request.env['custom_general_ledger.custom_general_ledger'].search([]),
#         })

#     @http.route('/custom_general_ledger/custom_general_ledger/objects/<model("custom_general_ledger.custom_general_ledger"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_general_ledger.object', {
#             'object': obj
#         })

