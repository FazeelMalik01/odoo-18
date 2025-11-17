# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPosLoyaltyExpiry(http.Controller):
#     @http.route('/custom_pos_loyalty_expiry/custom_pos_loyalty_expiry', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_pos_loyalty_expiry/custom_pos_loyalty_expiry/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_pos_loyalty_expiry.listing', {
#             'root': '/custom_pos_loyalty_expiry/custom_pos_loyalty_expiry',
#             'objects': http.request.env['custom_pos_loyalty_expiry.custom_pos_loyalty_expiry'].search([]),
#         })

#     @http.route('/custom_pos_loyalty_expiry/custom_pos_loyalty_expiry/objects/<model("custom_pos_loyalty_expiry.custom_pos_loyalty_expiry"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_pos_loyalty_expiry.object', {
#             'object': obj
#         })

