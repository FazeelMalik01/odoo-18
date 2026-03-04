# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    salary_computation_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('computed', 'Computed'),
    ], string='Salary Computation Type', default='fixed')
    salary_computation_rule_id = fields.Many2one(
        'custom__payroll.salary_calculation_rule',
        string='Salary Computation Rule',
        domain=[],
        help='Select a salary computation rule for calculated salary'
    )
    level = fields.Selection([
        ('level_1', 'Level 1'),
        ('level_2', 'Level 2'),
        ('level_3_single', 'Level 3 (Single)'),
        ('level_3_multiple', 'Level 3 (Multiple)'),
    ], string='Level', help='Level 3 (Single): Employee has 1 person under them. Level 3 (Multiple): Employee has 2 or more people under them.')
    employment_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('casual', 'Casual'),
    ], string='Type')
    pay_rate = fields.Selection([
        ('weekly', 'Weekly'),
        ('hourly', 'Hourly'),
    ], string='Pay Rate')
    age = fields.Integer(string='Age', compute='_compute_age', store=False, readonly=True)
    
    @api.depends('employee_id.birthday')
    def _compute_age(self):
        """Calculate age from employee's date of birth"""
        today = fields.Date.today()
        for contract in self:
            if contract.employee_id and contract.employee_id.birthday:
                birth_date = contract.employee_id.birthday
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                contract.age = age
            else:
                contract.age = 0

