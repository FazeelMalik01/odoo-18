# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    has_stocked_products = fields.Boolean(
        string='Has Stocked Products',
        compute='_compute_has_stocked_products',
        store=False,
        help='True if this category or any of its subcategories contains products with stock > 0'
    )
    
    
    def _get_all_descendants(self):
        """Get all descendant categories recursively"""
        descendants = self.env['product.public.category']
        if self.child_id:
            descendants |= self.child_id
            for child in self.child_id:
                descendants |= child._get_all_descendants()
        return descendants
    
    def get_website_children(self):
        """Return filtered child categories for website display"""
        if not self.child_id:
            return self.env['product.public.category']
        # Filter children to only show those with stocked products
        return self.child_id.filtered(lambda c: c.has_stocked_products)

    def _check_direct_stock(self, category):
        """
        Check if a category has stocked products directly assigned to it
        (not counting products in child categories)
        """
        # Get products directly in this category (use 'in' not 'child_of')
        products = self.env['product.template'].sudo().search([
            ('public_categ_ids', 'in', [category.id]),
            ('website_published', '=', True),
            ('sale_ok', '=', True)
        ])
        
        for product in products:
            # Check stock using stock.quant with sudo()
            # Use inventory_quantity_auto_apply if available, otherwise use quantity
            quants = self.env['stock.quant'].sudo().search([
                ('product_id', 'in', product.product_variant_ids.ids)
            ])
            
            # Check if any quant has quantity > 0 (actual physical stock)
            for quant in quants:
                if quant.quantity and quant.quantity > 0:
                    return True
                
                # Also check inventory_quantity_auto_apply (On Hand Quantity from view)
                if hasattr(quant, 'inventory_quantity_auto_apply') and quant.inventory_quantity_auto_apply:
                    if quant.inventory_quantity_auto_apply > 0:
                        return True
        return False

    @api.depends('child_id', 'product_tmpl_ids')
    def _compute_has_stocked_products(self):
        """
        Recursively check if this category or any of its subcategories
        contains products with quantity on hand > 0
        Uses stock.quant with sudo() to bypass access rights for website users
        
        Logic:
        - Check if category has stocked products directly assigned to it
        - If not, check if any child category (recursively) has stocked products
        """
        # Get all categories including all descendants to compute them all at once
        all_categories = self
        for cat in self:
            # Get all descendant categories recursively
            all_categories |= cat.child_id
            if cat.child_id:
                # Recursively add all descendants
                all_descendants = self.env['product.public.category']
                for child in cat.child_id:
                    all_descendants |= child
                    all_descendants |= child._get_all_descendants()
                all_categories |= all_descendants
        
        # First pass: compute direct stock for all categories
        direct_stock = {}
        for category in all_categories:
            direct_stock[category.id] = self._check_direct_stock(category)
        
        # Second pass: compute final result considering children
        # Process from leaf categories (no children) up to parents
        def compute_category_stock(category_id):
            """Recursively compute if category or any child has stock"""
            if category_id not in direct_stock:
                return False
            
            category = all_categories.browse(category_id)
            if not category.exists():
                return False
            
            # If category has direct stock, return True
            if direct_stock[category_id]:
                return True
            
            # Otherwise, check children
            if category.child_id:
                for child in category.child_id:
                    if compute_category_stock(child.id):
                        return True
            
            return False
        
        # Set the result for all categories
        for category in self:
            category.has_stocked_products = compute_category_stock(category.id)

