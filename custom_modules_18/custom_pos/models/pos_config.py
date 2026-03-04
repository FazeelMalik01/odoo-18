# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PosConfig(models.Model):
    _inherit = 'pos.config'


    # dual_currency_rate = fields.Float(string="USD → LBP Rate", default=89000)

    # existing fields...
    restrict_remove_line_employee_ids = fields.Many2many(
        'hr.employee',
        relation='restrict_remove_line_employee_pos_config_rel',
        string="Restrict Remove Line Control",
        help='Employees cannot access the Remove Line button.',
    )
    restrict_cancel_order_employee_ids = fields.Many2many(
        'hr.employee',
        relation='restrict_cancel_order_employee_pos_config_rel',
        string="Restrict Cancel Order Control",
        help='Employees cannot access the Cancel Order button.',
    )

    # NEW: restrict product info for selected employees (same pattern)
    restrict_product_info_employee_ids = fields.Many2many(
        'hr.employee',
        relation='restrict_product_info_employee_pos_config_rel',
        string="Restrict Product Info",
        help="Employees who cannot open Product Info from the POS.",
    )

    @api.onchange('basic_employee_ids', 'advanced_employee_ids')
    def _onchange_restrict_access_employee_ids(self):
        config_employee_ids = self.basic_employee_ids + self.advanced_employee_ids

        # remove any restrict_remove_line employees not in config employees
        for employee in list(self.restrict_remove_line_employee_ids):
            if employee not in config_employee_ids:
                self.restrict_remove_line_employee_ids -= employee

        # remove any restrict_cancel_order employees not in config employees
        for employee in list(self.restrict_cancel_order_employee_ids):
            if employee not in config_employee_ids:
                self.restrict_cancel_order_employee_ids -= employee

        # remove any restrict_product_info employees not in config employees
        for employee in list(self.restrict_product_info_employee_ids):
            if employee not in config_employee_ids:
                self.restrict_product_info_employee_ids -= employee
