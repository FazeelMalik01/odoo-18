# from odoo import http


# class CustomInalterableHash(http.Controller):
#     @http.route('/custom_inalterable_hash/custom_inalterable_hash', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_inalterable_hash/custom_inalterable_hash/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_inalterable_hash.listing', {
#             'root': '/custom_inalterable_hash/custom_inalterable_hash',
#             'objects': http.request.env['custom_inalterable_hash.custom_inalterable_hash'].search([]),
#         })

#     @http.route('/custom_inalterable_hash/custom_inalterable_hash/objects/<model("custom_inalterable_hash.custom_inalterable_hash"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_inalterable_hash.object', {
#             'object': obj
#         })

