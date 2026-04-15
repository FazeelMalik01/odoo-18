# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class GymEquipment(models.Model):
    """Gym Equipment"""
    _name = 'gym.equipment'
    _description = __doc__
    _rec_name = 'name'

    color = fields.Integer()
    avatar = fields.Binary()
    name = fields.Char(string="Equipment Name")
    exercise_for = fields.Many2many('exercise.for')
    serial_no = fields.Char(string="Serial No.")
    company_name = fields.Char()
    description = fields.Html()
    units = fields.Integer()
    cost = fields.Monetary()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency',
                                  related="company_id.currency_id")
