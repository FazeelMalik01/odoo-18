# -*- coding: utf-8 -*-
# from odoo import http


# class CustomAuthorizeGateway(http.Controller):
#     @http.route('/custom_authorize_gateway/custom_authorize_gateway', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_authorize_gateway/custom_authorize_gateway/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_authorize_gateway.listing', {
#             'root': '/custom_authorize_gateway/custom_authorize_gateway',
#             'objects': http.request.env['custom_authorize_gateway.custom_authorize_gateway'].search([]),
#         })

#     @http.route('/custom_authorize_gateway/custom_authorize_gateway/objects/<model("custom_authorize_gateway.custom_authorize_gateway"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_authorize_gateway.object', {
#             'object': obj
#         })

