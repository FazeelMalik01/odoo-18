# -*- coding: utf-8 -*-
# from odoo import http


# class CustomWebAddress(http.Controller):
#     @http.route('/custom_web_address/custom_web_address', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_web_address/custom_web_address/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_web_address.listing', {
#             'root': '/custom_web_address/custom_web_address',
#             'objects': http.request.env['custom_web_address.custom_web_address'].search([]),
#         })

#     @http.route('/custom_web_address/custom_web_address/objects/<model("custom_web_address.custom_web_address"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_web_address.object', {
#             'object': obj
#         })

