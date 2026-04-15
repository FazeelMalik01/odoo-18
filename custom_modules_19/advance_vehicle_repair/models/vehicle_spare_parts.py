from odoo import fields, models, api

class VehicleSpareParts(models.Model):
    _inherit = 'product.product'

    spare_part = fields.Boolean(string="Vehicle Spare part")
    part_condition = fields.Selection([
    ('new', 'New'),
    ('used', 'Used'),
    ('commercial', 'Commercial')
    ], string="Part Condition")
    linked_service_id = fields.Many2one('vehicle.services', string="Linked Auto-Service")
    vehicle_compatibility_ids = fields.One2many( 'product.vehicle.compatibility', 'product_id', string="Vehicle Compatibility Matrix")
    created_from_service = fields.Boolean(string="Created from Vehicle Service", default=False)

    def write(self, vals):
        for product in self:
            if product.created_from_service and 'type' in vals:
                # Remove type from vals to prevent editing
                vals.pop('type')
        return super(VehicleSpareParts, self).write(vals)
class VehicleSparePart(models.Model):
    _inherit = 'product.template'

    spare_part = fields.Boolean(string="Vehicle Spare part")
    @api.model
    def create(self, vals):
        template = super(VehicleSparePart, self).create(vals)
        self._sync_spare_part_to_variants(template)
        return template

    def write(self, vals):
        res = super(VehicleSparePart, self).write(vals)
        # Only sync if spare_part is updated
        if 'spare_part' in vals:
            for template in self:
                self._sync_spare_part_to_variants(template)
        return res

    def _sync_spare_part_to_variants(self, template):
        """Ensure spare_part is in product.product for this template"""
        Product = self.env['product.product']
        # If template has spare_part=True
        if template.spare_part:
            # Update existing variants
            template.product_variant_ids.write({'spare_part': True})
            # If no variants exist, create one
            if not template.product_variant_ids:
                Product.create({
                    'product_tmpl_id': template.id,
                    'spare_part': True,
                    'name': template.name,
                })
        else:
            # Optional: if spare_part=False, also remove from variants
            template.product_variant_ids.write({'spare_part': False})