# -*- coding: utf-8 -*-
# from odoo import http


# class CustomFalconRep(http.Controller):
#     @http.route('/custom_falcon_rep/custom_falcon_rep', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_falcon_rep/custom_falcon_rep/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_falcon_rep.listing', {
#             'root': '/custom_falcon_rep/custom_falcon_rep',
#             'objects': http.request.env['custom_falcon_rep.custom_falcon_rep'].search([]),
#         })

#     @http.route('/custom_falcon_rep/custom_falcon_rep/objects/<model("custom_falcon_rep.custom_falcon_rep"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_falcon_rep.object', {
#             'object': obj
#         })

