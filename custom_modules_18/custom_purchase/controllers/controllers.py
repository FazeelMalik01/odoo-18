# -*- coding: utf-8 -*-
from odoo import http

class CustomPurchaseController(http.Controller):
    @http.route('/custom_purchase/custom_purchase/', auth='public')
    def index(self, **kw):
        return "Hello, Falcon Purchase Request!"
