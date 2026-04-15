from odoo import models, fields, api

class ProductVehicleCompatibility(models.Model):
    _name = 'product.vehicle.compatibility'
    _description = 'Vehicle Compatibility Matrix'

    product_id = fields.Many2one('product.product', string="Product", required=True, ondelete='cascade')
    make_id = fields.Many2one('vehicle.brand', string="Make")
    model_id = fields.Many2one('vehicle.model', string="Model")
    model_year_ids = fields.Many2many(
        'vehicle.model.year',
        string="Model Years",
        widget="many2many_tags"
    )
    @api.onchange('make_id')
    def _onchange_make(self):
        """Filter model_id to only show models for the selected make."""
        for record in self:
            if record.make_id:
                # Set domain on model_id
                return {'domain': {'model_id': [('brand_id', '=', record.make_id.id)]}}
            else:
                return {'domain': {'model_id': []}}

    @api.onchange('make_id', 'model_id')
    def _onchange_model_years(self):
        """Populate available model_year_ids from vehicle.register."""
        for record in self:
            if record.make_id and record.model_id:
                year_ids = self.env['vehicle.register'].search([
                    ('brand_id', '=', record.make_id.id),
                    ('model_id', '=', record.model_id.id)
                ]).mapped('model_year.id')
                record.model_year_ids = [(6, 0, year_ids)]
            else:
                record.model_year_ids = [(5, 0, 0)]
    
class VehicleModelYear(models.Model):
    _name = 'vehicle.model.year'
    _description = 'Vehicle Model Year'

    name = fields.Char(string="Year", required=True)