# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class custom_falcon_rep(models.Model):
#     _name = 'custom_falcon_rep.custom_falcon_rep'
#     _description = 'custom_falcon_rep.custom_falcon_rep'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

