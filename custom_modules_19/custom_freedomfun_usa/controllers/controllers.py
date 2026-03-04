# from odoo import http


# class CustomFreedomfunUsa(http.Controller):
#     @http.route('/custom_freedomfun_usa/custom_freedomfun_usa', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_freedomfun_usa/custom_freedomfun_usa/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_freedomfun_usa.listing', {
#             'root': '/custom_freedomfun_usa/custom_freedomfun_usa',
#             'objects': http.request.env['custom_freedomfun_usa.custom_freedomfun_usa'].search([]),
#         })

#     @http.route('/custom_freedomfun_usa/custom_freedomfun_usa/objects/<model("custom_freedomfun_usa.custom_freedomfun_usa"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_freedomfun_usa.object', {
#             'object': obj
#         })

