# -*- coding: utf-8 -*-
from odoo import models, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _load_pos_data(self, data):
        result = super()._load_pos_data(data)
        # find config id from payload if present:
        try:
            config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        except Exception:
            config_id = None

        restrict_remove = config_id.restrict_remove_line_employee_ids.ids if config_id else []
        restrict_cancel = config_id.restrict_cancel_order_employee_ids.ids if config_id else []
        restrict_product_info = config_id.restrict_product_info_employee_ids.ids if config_id else []

        for employee in result.get('data', []):
            emp_id = employee.get('id')
            if not emp_id:
                continue
            employee['_is_restrict_remove_line'] = emp_id in restrict_remove
            employee['_is_restrict_cancel_order'] = emp_id in restrict_cancel
            employee['_is_restrict_product_info'] = emp_id in restrict_product_info
        return result
