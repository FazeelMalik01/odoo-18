# -*- coding: utf-8 -*-
# from odoo import http


# class ZktecoAttendance(http.Controller):
#     @http.route('/zkteco_attendance/zkteco_attendance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zkteco_attendance/zkteco_attendance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zkteco_attendance.listing', {
#             'root': '/zkteco_attendance/zkteco_attendance',
#             'objects': http.request.env['zkteco_attendance.zkteco_attendance'].search([]),
#         })

#     @http.route('/zkteco_attendance/zkteco_attendance/objects/<model("zkteco_attendance.zkteco_attendance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zkteco_attendance.object', {
#             'object': obj
#         })

