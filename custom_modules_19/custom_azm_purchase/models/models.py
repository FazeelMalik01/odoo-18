# from odoo import models, fields, api


# class custom_azm_purchase(models.Model):
#     _name = 'custom_azm_purchase.custom_azm_purchase'
#     _description = 'custom_azm_purchase.custom_azm_purchase'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

