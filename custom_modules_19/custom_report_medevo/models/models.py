# from odoo import models, fields, api


# class custom_report_medevo(models.Model):
#     _name = 'custom_report_medevo.custom_report_medevo'
#     _description = 'custom_report_medevo.custom_report_medevo'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100


from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    client_order_ref = fields.Char(string='PO Number')


class AccountMove(models.Model):
    _inherit = 'account.move'

    ref = fields.Char(string='PO Number')

