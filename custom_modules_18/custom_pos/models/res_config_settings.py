# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # dual_currency_rate = fields.Float(related='pos_config_id.dual_currency_rate',
    #     string="USD → LBP Rate",readonly=False)


    pos_restrict_remove_line_employee_ids = fields.Many2many(
        related='pos_config_id.restrict_remove_line_employee_ids',
        relation='restrict_remove_line_employee_res_config_settings_rel',
        string="Restrict Remove Line Control",
        readonly=False,
    )
    pos_restrict_cancel_order_employee_ids = fields.Many2many(
        related='pos_config_id.restrict_cancel_order_employee_ids',
        relation='restrict_cancel_order_employee_res_config_settings_rel',
        string="Restrict Cancel Order Control",
        readonly=False,
    )

    # NEW: employee-level restrict product info
    pos_restrict_product_info_employee_ids = fields.Many2many(
        related='pos_config_id.restrict_product_info_employee_ids',
        relation='restrict_product_info_employee_res_config_settings_rel',
        string="Restrict Product Info",
        readonly=False,
        help="Select employees who cannot open Product Info in POS.",
    )


    @api.onchange('pos_basic_employee_ids', 'pos_advanced_employee_ids')
    def _onchange_pos_restrict_access_employee_ids(self):
        config_employee_ids = self.pos_basic_employee_ids + self.pos_advanced_employee_ids

        for employee in list(self.pos_restrict_remove_line_employee_ids):
            if employee not in config_employee_ids:
                self.pos_restrict_remove_line_employee_ids -= employee

        for employee in list(self.pos_restrict_cancel_order_employee_ids):
            if employee not in config_employee_ids:
                self.pos_restrict_cancel_order_employee_ids -= employee

        for employee in list(self.pos_restrict_product_info_employee_ids):
            if employee not in config_employee_ids:
                self.pos_restrict_product_info_employee_ids -= employee
