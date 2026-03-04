# -*- coding: utf-8 -*-
# from odoo import http


# class ZktecoRemoteAttendance(http.Controller):
#     @http.route('/zkteco_remote_attendance/zkteco_remote_attendance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zkteco_remote_attendance/zkteco_remote_attendance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zkteco_remote_attendance.listing', {
#             'root': '/zkteco_remote_attendance/zkteco_remote_attendance',
#             'objects': http.request.env['zkteco_remote_attendance.zkteco_remote_attendance'].search([]),
#         })

#     @http.route('/zkteco_remote_attendance/zkteco_remote_attendance/objects/<model("zkteco_remote_attendance.zkteco_remote_attendance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zkteco_remote_attendance.object', {
#             'object': obj
#         })

