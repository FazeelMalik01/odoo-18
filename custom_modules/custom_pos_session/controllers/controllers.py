# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPosSession(http.Controller):
#     @http.route('/custom_pos_session/custom_pos_session', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_pos_session/custom_pos_session/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_pos_session.listing', {
#             'root': '/custom_pos_session/custom_pos_session',
#             'objects': http.request.env['custom_pos_session.custom_pos_session'].search([]),
#         })

#     @http.route('/custom_pos_session/custom_pos_session/objects/<model("custom_pos_session.custom_pos_session"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_pos_session.object', {
#             'object': obj
#         })

