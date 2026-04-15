# from odoo import http


# class CustomApprovals(http.Controller):
#     @http.route('/custom_approvals/custom_approvals', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_approvals/custom_approvals/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_approvals.listing', {
#             'root': '/custom_approvals/custom_approvals',
#             'objects': http.request.env['custom_approvals.custom_approvals'].search([]),
#         })

#     @http.route('/custom_approvals/custom_approvals/objects/<model("custom_approvals.custom_approvals"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_approvals.object', {
#             'object': obj
#         })

