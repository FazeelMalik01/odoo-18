from odoo import models, fields
from odoo.tools import unique


class AccountFiscalPosition(models.Model):
    """Extend fiscal positions with our own tax mapping lines."""

    _inherit = "account.fiscal.position"

    custom_tax_mapping_ids = fields.One2many(
        comodel_name="account.fiscal.position.tax.map",
        inverse_name="fiscal_position_id",
        string="Tax Mapping",
    )

    def map_tax(self, taxes):
        """Override map_tax to use our custom tax mapping first, then fall back to standard mapping."""
        if not self:
            return taxes
        if not self.tax_ids and not self.custom_tax_mapping_ids:
            # Empty fiscal positions (like those created by tax units) remove all taxes
            return self.env['account.tax']
        
        # Build a mapping dictionary from our custom tax mappings
        custom_tax_map = {}
        if self.custom_tax_mapping_ids:
            for mapping in self.custom_tax_mapping_ids:
                src_id = mapping.tax_src_id.id
                dest_id = mapping.tax_dest_id.id
                if src_id not in custom_tax_map:
                    custom_tax_map[src_id] = []
                custom_tax_map[src_id].append(dest_id)
        
        # Get standard tax_map for fallback
        standard_tax_map = self.tax_map or {}
        
        # Process each tax: use custom mapping if available, otherwise use standard mapping
        mapped_tax_ids = []
        for tax in taxes:
            if tax.id in custom_tax_map:
                # Use our custom mapping
                mapped_tax_ids.extend(custom_tax_map[tax.id])
            else:
                # No custom mapping, use standard Odoo tax_map
                mapped_tax_ids.extend(standard_tax_map.get(tax.id, [tax.id]))
        
        # Return unique tax IDs (following Odoo's pattern)
        return self.env['account.tax'].browse(list(unique(mapped_tax_ids)))


class AccountFiscalPositionTaxMap(models.Model):
    """Custom tax mapping lines."""

    _name = "account.fiscal.position.tax.map"
    _description = "Fiscal Position Tax Mapping"

    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        string="Fiscal Position",
        required=True,
        ondelete="cascade",
    )
    tax_src_id = fields.Many2one(
        comodel_name="account.tax",
        string="Tax on Product",
        required=True,
    )
    tax_dest_id = fields.Many2one(
        comodel_name="account.tax",
        string="Tax to Apply",
        required=True,
    )

