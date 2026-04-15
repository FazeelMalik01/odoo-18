# from odoo import http


# class CustomReportMedevo(http.Controller):
#     @http.route('/custom_report_medevo/custom_report_medevo', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_report_medevo/custom_report_medevo/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_report_medevo.listing', {
#             'root': '/custom_report_medevo/custom_report_medevo',
#             'objects': http.request.env['custom_report_medevo.custom_report_medevo'].search([]),
#         })

#     @http.route('/custom_report_medevo/custom_report_medevo/objects/<model("custom_report_medevo.custom_report_medevo"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_report_medevo.object', {
#             'object': obj
#         })

