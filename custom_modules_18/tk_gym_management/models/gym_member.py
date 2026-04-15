# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GymMember(models.Model):
    """Gym Member"""
    _inherit = 'res.partner'
    _description = __doc__

    is_member = fields.Boolean(string='Member')
    trainer_id = fields.Many2one('hr.employee', domain=[('is_trainer', '=', True)],
                                 string='Support Trainer')
    birthdate = fields.Date()
    age = fields.Integer(compute='_compute_member_age')
    gender = fields.Selection([('m', 'Male'), ('f', 'Female'), ('o', 'Other')])
    member_report_ids = fields.One2many('fitness.report', 'member_id')
    diet_plan_ids = fields.One2many('diet.plan', 'member_id', string='Diet Plan Report')
    reports_count = fields.Integer(string='Fitness Reports', compute='_compute_get_reports_count')
    diet_schedule = fields.Integer(string='Diet Plan', compute='_compute_get_diet_schedule_count')
    workout_ids = fields.Many2many('gym.workout', string='Workout Plans')

    membership_count = fields.Integer(compute="_compute_membership_count")
    gym_hours_per_day = fields.Float(string='Gym Hours/Day')

    def _compute_membership_count(self):
        """compute membership count"""
        for rec in self:
            count = self.env['memberships.member'].search_count([('gym_member_id', '=', rec.id)])
            rec.membership_count = count

    def action_view_memberships(self):
        """action view memberships"""
        return {
            'name': 'Memberships',
            'domain': [('gym_member_id', '=', self.id)],
            'res_model': 'memberships.member',
            'view_id': False,
            'view_mode': 'list,form',
            'type': "ir.actions.act_window"
        }

    def gym_member_reports(self):
        """gym member reports"""
        return {
            'name': 'Reports',
            'domain': [('member_id', '=', self.id)],
            'res_model': 'fitness.report',
            'view_id': False,
            'view_mode': 'list,form',
            'type': "ir.actions.act_window"
        }

    def _compute_get_reports_count(self):
        """get reports count"""
        for rec in self:
            count = self.env['fitness.report'].search_count([('member_id', '=', rec.id)])
            rec.reports_count = count

    def gym_member_diet_schedule(self):
        """gym member diet schedule"""
        return {
            'name': 'Schedule',
            'domain': [('member_id', '=', self.id)],
            'res_model': 'diet.plan',
            'view_id': False,
            'view_mode': 'list,form',
            'type': "ir.actions.act_window"
        }

    def _compute_get_diet_schedule_count(self):
        """get diet schedule count"""
        for rec in self:
            count = self.env['diet.plan'].search_count([('member_id', '=', rec.id)])
            rec.diet_schedule = count

    @api.depends('birthdate')
    def _compute_member_age(self):
        """member age"""
        today_date = datetime.date.today()
        for rec in self:
            if rec.birthdate:
                birthdate = fields.Datetime.to_datetime(rec.birthdate).date()
                age_data = int((today_date - birthdate).days / 365)
                rec.age = age_data
            else:
                rec.age = 0

    @api.constrains('gym_hours_per_day')
    def _check_gym_hours_per_day(self):
        """check gym hours per day"""
        for rec in self:
            if rec.gym_hours_per_day > 24 or rec.gym_hours_per_day <= 0:
                raise ValidationError(
                    _("Gym hours per day must be between 1 and 24 hours. It cannot be greater "
                      "than 24 or less than or equal to 0 hours."))
