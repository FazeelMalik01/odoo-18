# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPayroll(http.Controller):
#     @http.route('/custom__payroll/custom__payroll', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom__payroll/custom__payroll/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom__payroll.listing', {
#             'root': '/custom__payroll/custom__payroll',
#             'objects': http.request.env['custom__payroll.custom__payroll'].search([]),
#         })

#     @http.route('/custom__payroll/custom__payroll/objects/<model("custom__payroll.custom__payroll"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom__payroll.object', {
#             'object': obj
#         })

