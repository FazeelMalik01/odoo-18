# from odoo import http


# class CustomFieldService(http.Controller):
#     @http.route('/custom_field_service/custom_field_service', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_field_service/custom_field_service/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_field_service.listing', {
#             'root': '/custom_field_service/custom_field_service',
#             'objects': http.request.env['custom_field_service.custom_field_service'].search([]),
#         })

#     @http.route('/custom_field_service/custom_field_service/objects/<model("custom_field_service.custom_field_service"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_field_service.object', {
#             'object': obj
#         })

