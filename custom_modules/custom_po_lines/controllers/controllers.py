# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPoLines(http.Controller):
#     @http.route('/custom_po_lines/custom_po_lines', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_po_lines/custom_po_lines/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_po_lines.listing', {
#             'root': '/custom_po_lines/custom_po_lines',
#             'objects': http.request.env['custom_po_lines.custom_po_lines'].search([]),
#         })

#     @http.route('/custom_po_lines/custom_po_lines/objects/<model("custom_po_lines.custom_po_lines"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_po_lines.object', {
#             'object': obj
#         })

