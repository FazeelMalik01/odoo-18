# -*- coding: utf-8 -*-

from odoo import models, fields


class SalaryCalculationRule(models.Model):
    _name = 'custom__payroll.salary_calculation_rule'
    _description = 'Salary Calculation Rules'

    name = fields.Char(string='Title', required=True)
    under_16_ids = fields.One2many(
        'custom__payroll.salary_calculation_rule.under_16',
        'rule_id',
        string='Under 16 Age Classifications'
    )
    age_16_ids = fields.One2many(
        'custom__payroll.salary_calculation_rule.age_16',
        'rule_id',
        string='16 Age Classifications'
    )
    age_17_ids = fields.One2many(
        'custom__payroll.salary_calculation_rule.age_17',
        'rule_id',
        string='17 Age Classifications'
    )
    age_18_ids = fields.One2many(
        'custom__payroll.salary_calculation_rule.age_18',
        'rule_id',
        string='18 Age Classifications'
    )
    age_19_ids = fields.One2many(
        'custom__payroll.salary_calculation_rule.age_19',
        'rule_id',
        string='19 Age Classifications'
    )
    age_20_ids = fields.One2many(
        'custom__payroll.salary_calculation_rule.age_20',
        'rule_id',
        string='20 Age Classifications'
    )
    adults_ids = fields.One2many(
        'custom__payroll.salary_calculation_rule.adults',
        'rule_id',
        string='Adults Classifications'
    )

