# from odoo import models, fields, api


# class custom_autocad_timer(models.Model):
#     _name = 'custom_autocad_timer.custom_autocad_timer'
#     _description = 'custom_autocad_timer.custom_autocad_timer'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

