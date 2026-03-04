from odoo import models, fields

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    specifications = fields.Char(string="Specifications")
    manufacturer = fields.Char(string="Manufacturer")
    product_no = fields.Char(string="Product No")
    lead_time = fields.Char(string="Lead Time")
