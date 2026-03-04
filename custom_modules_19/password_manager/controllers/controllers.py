# from odoo import http


# class PasswordManager(http.Controller):
#     @http.route('/password_manager/password_manager', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/password_manager/password_manager/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('password_manager.listing', {
#             'root': '/password_manager/password_manager',
#             'objects': http.request.env['password_manager.password_manager'].search([]),
#         })

#     @http.route('/password_manager/password_manager/objects/<model("password_manager.password_manager"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('password_manager.object', {
#             'object': obj
#         })

