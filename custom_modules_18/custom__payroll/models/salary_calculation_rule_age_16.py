# -*- coding: utf-8 -*-

from odoo import models, fields


class SalaryCalculationRuleAge16(models.Model):
    _name = 'custom__payroll.salary_calculation_rule.age_16'
    _description = '16 Age Classification'
    _order = 'classification, employment_type'

    rule_id = fields.Many2one('custom__payroll.salary_calculation_rule', string='Rule', required=True, ondelete='cascade')
    age_from = fields.Integer(string='Age From', required=True)
    age_to = fields.Integer(string='Age To', required=True)
    employment_type = fields.Selection([
        ('casual', 'Casual'),
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
    ], string='Type', required=True, default='full_time')
    classification = fields.Selection([
        ('level_1', 'Level 1'),
        ('level_2', 'Level 2'),
        ('level_3_single', 'Level 3 (Single)'),
        ('level_3_multiple', 'Level 3 (Multiple)'),
    ], string='Classification', required=True, default='level_1')
    weekly_pay_rate = fields.Float(string='Weekly Pay Rate', required=True)
    hourly_pay_rate = fields.Float(string='Hourly Pay Rate', required=True)
    evening_work_rate = fields.Float(
        string='Evening Work Rate (Mon-Fri, 10pm-12am)',
        required=True,
        help='Rate for evening work from Monday to Friday, 10pm to midnight'
    )
    evening_work_rate_midnight = fields.Float(
        string='Evening Work Rate (Mon-Fri, 12am-6am)',
        required=True,
        help='Rate for evening work from Monday to Friday, midnight to 6am'
    )
    saturday_rate = fields.Float(
        string='Saturday Rate',
        required=True,
        help='Rate for work on Saturdays'
    )
    sunday_rate = fields.Float(
        string='Sunday Rate',
        required=True,
        help='Rate for work on Sundays'
    )
    overtime_first_2_hours = fields.Float(
        string='Overtime - First 2 Hours',
        required=True,
        default=0.0,
        help='Overtime rate for the first 2 hours of overtime work'
    )
    overtime_after_2_hours = fields.Float(
        string='Overtime - After 2 Hours',
        required=True,
        default=0.0,
        help='Overtime rate for hours after the first 2 hours of overtime work'
    )
    overtime_sunday = fields.Float(
        string='Overtime - Sunday',
        required=True,
        default=0.0,
        help='Overtime rate for work on Sundays'
    )
    public_holiday_rate = fields.Float(
        string='Public Holiday',
        required=True,
        default=0.0,
        help='Rate for work on public holidays'
    )
    overtime_public_holiday = fields.Float(
        string='Overtime - Public Holiday',
        required=True,
        default=0.0,
        help='Overtime rate for work on public holidays'
    )

