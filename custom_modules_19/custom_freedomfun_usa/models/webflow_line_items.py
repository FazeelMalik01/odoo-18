from odoo import models, fields, api


class WebflowLineItem(models.Model):
    _name = "webflow.line.item"
    _description = "Webflow Line Item"

    product_tmpl_id = fields.Many2one("product.template", ondelete="cascade")
    line_item_id = fields.Char("Line Item ID")
