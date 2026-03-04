# -*- coding: utf-8 -*-
from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        result['search_params']['fields'].extend([
            'restrict_remove_line_employee_ids',
            'restrict_cancel_order_employee_ids',
            'restrict_product_info_employee_ids',
        ])
        return result

    def _pos_ui_pos_config(self, config):
        result = super()._pos_ui_pos_config(config)
        result['restrict_remove_line_employee_ids'] = config.restrict_remove_line_employee_ids.ids
        result['restrict_cancel_order_employee_ids'] = config.restrict_cancel_order_employee_ids.ids
        result['restrict_product_info_employee_ids'] = config.restrict_product_info_employee_ids.ids
        return result
