# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GymTrainer(models.Model):
    """Gym Trainer"""
    _inherit = 'hr.employee'
    _description = __doc__
    _rec_name = 'name'

    is_trainer = fields.Boolean(string='Trainer')
    member_count = fields.Integer(string='Count', compute='_compute_get_member_count')
    working_hours_per_day = fields.Float(string='Working Hours/Day')

    def _compute_get_member_count(self):
        """get member count"""
        count = self.env['res.partner'].search_count([('trainer_id', '=', self.id)])
        self.member_count = count

    def gym_member(self):
        """gym member"""
        return {
            'type': "ir.actions.act_window",
            'name': _('Member'),
            'domain': [('trainer_id', '=', self.id)],
            'res_model': 'res.partner',
            'view_id': False,
            'view_mode': 'list,form',
        }

    @api.constrains('working_hours_per_day')
    def _check_gym_hours_per_day(self):
        """check gym hours per day"""
        for rec in self:
            if rec.working_hours_per_day > 24 or rec.working_hours_per_day <= 0:
                raise ValidationError(
                    _("Working hours per day must be between 1 and 24 hours. It cannot be greater "
                      "than 24 or less than or equal to 0 hours."))
