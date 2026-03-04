# from odoo import http


# class CustomAzmPurchase(http.Controller):
#     @http.route('/custom_azm_purchase/custom_azm_purchase', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_azm_purchase/custom_azm_purchase/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_azm_purchase.listing', {
#             'root': '/custom_azm_purchase/custom_azm_purchase',
#             'objects': http.request.env['custom_azm_purchase.custom_azm_purchase'].search([]),
#         })

#     @http.route('/custom_azm_purchase/custom_azm_purchase/objects/<model("custom_azm_purchase.custom_azm_purchase"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_azm_purchase.object', {
#             'object': obj
#         })

