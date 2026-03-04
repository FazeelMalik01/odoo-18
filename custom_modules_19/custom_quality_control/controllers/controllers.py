# from odoo import http


# class CustomQualityControl(http.Controller):
#     @http.route('/custom_quality_control/custom_quality_control', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_quality_control/custom_quality_control/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_quality_control.listing', {
#             'root': '/custom_quality_control/custom_quality_control',
#             'objects': http.request.env['custom_quality_control.custom_quality_control'].search([]),
#         })

#     @http.route('/custom_quality_control/custom_quality_control/objects/<model("custom_quality_control.custom_quality_control"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_quality_control.object', {
#             'object': obj
#         })

