# from odoo import http


# class CustomReports(http.Controller):
#     @http.route('/custom_reports/custom_reports', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_reports/custom_reports/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_reports.listing', {
#             'root': '/custom_reports/custom_reports',
#             'objects': http.request.env['custom_reports.custom_reports'].search([]),
#         })

#     @http.route('/custom_reports/custom_reports/objects/<model("custom_reports.custom_reports"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_reports.object', {
#             'object': obj
#         })

