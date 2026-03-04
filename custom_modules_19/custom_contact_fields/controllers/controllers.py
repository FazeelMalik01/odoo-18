# from odoo import http


# class CustomContactFields(http.Controller):
#     @http.route('/custom_contact_fields/custom_contact_fields', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_contact_fields/custom_contact_fields/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_contact_fields.listing', {
#             'root': '/custom_contact_fields/custom_contact_fields',
#             'objects': http.request.env['custom_contact_fields.custom_contact_fields'].search([]),
#         })

#     @http.route('/custom_contact_fields/custom_contact_fields/objects/<model("custom_contact_fields.custom_contact_fields"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_contact_fields.object', {
#             'object': obj
#         })

