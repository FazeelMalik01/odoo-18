# from odoo import models, fields, api


# class custom_freedomfun_usa(models.Model):
#     _name = 'custom_freedomfun_usa.custom_freedomfun_usa'
#     _description = 'custom_freedomfun_usa.custom_freedomfun_usa'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

