# -*- coding: utf-8 -*-
# from odoo import http


# class CustomInventorySettings(http.Controller):
#     @http.route('/custom_inventory_settings/custom_inventory_settings', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_inventory_settings/custom_inventory_settings/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_inventory_settings.listing', {
#             'root': '/custom_inventory_settings/custom_inventory_settings',
#             'objects': http.request.env['custom_inventory_settings.custom_inventory_settings'].search([]),
#         })

#     @http.route('/custom_inventory_settings/custom_inventory_settings/objects/<model("custom_inventory_settings.custom_inventory_settings"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_inventory_settings.object', {
#             'object': obj
#         })

