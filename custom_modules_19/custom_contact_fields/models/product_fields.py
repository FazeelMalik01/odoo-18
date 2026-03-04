from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    length = fields.Float(string="Length")
    width = fields.Float(string="Width")
    height = fields.Float(string="Height")

    volume = fields.Float(
        string="Volume",
        compute="_compute_volume",
        store=True
    )

    @api.depends('length', 'width', 'height')
    def _compute_volume(self):
        for record in self:
            record.volume = record.length * record.width * record.height