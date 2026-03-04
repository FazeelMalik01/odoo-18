# from odoo import http


# class CustomAccountsTax(http.Controller):
#     @http.route('/custom_accounts_tax/custom_accounts_tax', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_accounts_tax/custom_accounts_tax/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_accounts_tax.listing', {
#             'root': '/custom_accounts_tax/custom_accounts_tax',
#             'objects': http.request.env['custom_accounts_tax.custom_accounts_tax'].search([]),
#         })

#     @http.route('/custom_accounts_tax/custom_accounts_tax/objects/<model("custom_accounts_tax.custom_accounts_tax"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_accounts_tax.object', {
#             'object': obj
#         })

