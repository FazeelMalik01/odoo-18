# -*- coding: utf-8 -*-

from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _has_stock(self):
        """
        Check if product has stock > 0 using stock.quant with sudo()
        Uses quantity field (actual physical quantity) as primary check
        """
        try:
            self.ensure_one()
            
            # Get all quants for product variants
            quants = self.env['stock.quant'].sudo().search([
                ('product_id', 'in', self.product_variant_ids.ids)
            ])
            
            if not quants:
                return False
            
            # Check quantity field first (actual physical stock)
            for quant in quants:
                if quant.quantity and quant.quantity > 0:
                    return True
                
                # Also check inventory_quantity_auto_apply (On Hand Quantity from view)
                if hasattr(quant, 'inventory_quantity_auto_apply'):
                    if quant.inventory_quantity_auto_apply and quant.inventory_quantity_auto_apply > 0:
                        return True
            
            return False
        except Exception:
            # If there's any error, return True to be safe (don't hide products on error)
            return True

    @api.model
    def _search_get_detail(self, website, order, options):
        """
        Override to filter out products with 0 on-hand quantity from website shop
        Note: We cannot use qty_available in domain as it requires warehouse access.
        Instead, we'll filter products after the search in the controller.
        """
        res = super(ProductTemplate, self)._search_get_detail(website, order, options)
        # Don't add qty_available filter here as it requires warehouse access
        # Filtering will be done in the controller after search
        return res
