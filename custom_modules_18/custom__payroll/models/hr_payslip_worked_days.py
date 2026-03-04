# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    # Add a field to track if amount was manually set (to prevent recomputation)
    amount_manually_set = fields.Boolean(string='Amount Manually Set', default=False, store=True)

    @api.depends('is_paid', 'is_credit_time', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours', 'amount_manually_set')
    def _compute_amount(self):
        """
        Override compute_amount to prevent recomputation for custom computed payslips
        If amount_manually_set is True OR if the payslip uses custom computation, skip the standard computation
        """
        # Filter records that should NOT be recomputed
        # 1. Records with amount_manually_set = True
        # 2. Records where payslip contract uses custom computation
        skip_compute = self.filtered(lambda r: 
            r.amount_manually_set or 
            (r.payslip_id and r.payslip_id.contract_id and r.payslip_id.contract_id.salary_computation_type == 'computed')
        )
        
        # Records that should use standard computation
        standard_records = self - skip_compute
        
        # Call parent compute ONLY for standard records
        if standard_records:
            super(HrPayslipWorkedDays, standard_records)._compute_amount()
        
        # For manually set amounts or custom computed payslips, keep the existing amount
        # Don't recompute it - the amount was already set correctly in hr_payslip.py
        for record in skip_compute:
            # The amount is already set correctly, just ensure it's not overwritten
            # If amount is 0 but should have a value, it means it wasn't set yet
            # In that case, we'll let it be 0 (shouldn't happen if our code works correctly)
            pass

