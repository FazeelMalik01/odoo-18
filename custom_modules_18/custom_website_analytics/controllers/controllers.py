# -*- coding: utf-8 -*-
# from odoo import http


# class CustomWebsiteAnalytics(http.Controller):
#     @http.route('/custom_website_analytics/custom_website_analytics', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_website_analytics/custom_website_analytics/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_website_analytics.listing', {
#             'root': '/custom_website_analytics/custom_website_analytics',
#             'objects': http.request.env['custom_website_analytics.custom_website_analytics'].search([]),
#         })

#     @http.route('/custom_website_analytics/custom_website_analytics/objects/<model("custom_website_analytics.custom_website_analytics"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_website_analytics.object', {
#             'object': obj
#         })

