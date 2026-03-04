# from odoo import http


# class CustomDealersPortal(http.Controller):
#     @http.route('/custom_dealers_portal/custom_dealers_portal', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_dealers_portal/custom_dealers_portal/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_dealers_portal.listing', {
#             'root': '/custom_dealers_portal/custom_dealers_portal',
#             'objects': http.request.env['custom_dealers_portal.custom_dealers_portal'].search([]),
#         })

#     @http.route('/custom_dealers_portal/custom_dealers_portal/objects/<model("custom_dealers_portal.custom_dealers_portal"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_dealers_portal.object', {
#             'object': obj
#         })

