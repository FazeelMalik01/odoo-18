from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    length = fields.Float(string="Length")
    width = fields.Float(string="Width")
    height = fields.Float(string="Height")
    volume = fields.Float(string="Volume", compute="_compute_volume", store=True)

    # Display units next to the dimension values, reusing the company's volume unit
    length_uom_name = fields.Char(string=" ", compute="_compute_dimension_uom_name", readonly=True)
    width_uom_name = fields.Char(string=" ", compute="_compute_dimension_uom_name", readonly=True)
    height_uom_name = fields.Char(string=" ", compute="_compute_dimension_uom_name", readonly=True)

    default_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Default Warehouse",
        help="Warehouse that will be automatically selected in Sale and Purchase order lines."
    )

    @api.depends('length', 'width', 'height')
    def _compute_volume(self):
        for record in self:
            record.volume = record.length * record.width * record.height

    @api.depends_context('company')
    def _compute_dimension_uom_name(self):
        """Use the same unit family as the company's volume unit (m³ → m, ft³ → ft)."""
        company = self.env.company
        volume_uom_name = (getattr(company, 'volume_uom_name', '') or '').lower()

        if 'ft' in volume_uom_name or 'foot' in volume_uom_name:
            linear_unit = 'ft'
        elif 'cm' in volume_uom_name:
            linear_unit = 'cm'
        elif 'mm' in volume_uom_name:
            linear_unit = 'mm'
        else:
            # default to meters for m³ and unknown ones
            linear_unit = 'm'

        for record in self:
            record.length_uom_name = linear_unit
            record.width_uom_name = linear_unit
            record.height_uom_name = linear_unit