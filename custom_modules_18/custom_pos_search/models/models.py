# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('name', 'default_code', 'barcode', 'product_tmpl_id')
    @api.depends_context('display_default_code', 'seller_id', 'company_id', 'partner_id')
    def _compute_display_name(self):
        """Override to show barcode instead of reference (default_code) in selection dropdowns"""
        # Call parent to get the standard display name
        super(ProductProduct, self)._compute_display_name()
        
        # Then modify to use barcode instead of default_code if barcode exists
        for product in self:
            if product.barcode and self._context.get('display_default_code', True):
                # Replace [default_code] with [barcode] in display_name
                display_name = product.display_name
                # Check if display_name has [code] format and replace it
                if display_name.startswith('[') and ']' in display_name:
                    # Extract the name part (everything after the first '] ')
                    parts = display_name.split('] ', 1)
                    if len(parts) > 1:
                        # Replace the code part with barcode
                        product.display_name = f'[{product.barcode}] {parts[1]}'
                    else:
                        # If format is different, just prepend barcode
                        product.display_name = f'[{product.barcode}] {display_name}'
                else:
                    # No [code] prefix, prepend barcode
                    product.display_name = f'[{product.barcode}] {display_name}'

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        """
        Override _name_search to include packaging barcodes in search.
        This allows POS to find products by their packaging barcodes.
        """
        # First, perform the standard name search
        result = super(ProductProduct, self)._name_search(name, args, operator, limit, order)
        
        # If name is provided, also search in packaging barcodes
        if name and len(name.strip()) > 0:
            name = name.strip()
            
            # For exact match searches (like barcode scans), use '=' operator
            # For partial searches, use the provided operator
            if operator in ['=', 'ilike']:
                barcode_operator = '='
            else:
                barcode_operator = operator
            
            # Search for products by their own barcode
            barcode_domain = expression.AND([
                args or [],
                [('barcode', barcode_operator, name)]
            ])
            barcode_product_ids = self._search(barcode_domain, limit=limit, order=order)
            
            # Search in packaging barcodes
            packaging_domain = [('barcode', barcode_operator, name)]
            packagings = self.env['product.packaging'].search(packaging_domain)
            packaging_product_ids = []
            if packagings:
                # Get product IDs from packagings
                # Packaging can be linked via product_id (product.product) or product_tmpl_id (product.template)
                for packaging in packagings:
                    if hasattr(packaging, 'product_id') and packaging.product_id:
                        packaging_product_ids.append(packaging.product_id.id)
                    elif hasattr(packaging, 'product_tmpl_id') and packaging.product_tmpl_id:
                        # If only template is set, get all variants
                        variants = self.env['product.product'].search([
                            ('product_tmpl_id', '=', packaging.product_tmpl_id.id)
                        ])
                        packaging_product_ids.extend(variants.ids)
            
            # If we found products via packaging barcodes, add them to search
            if packaging_product_ids:
                packaging_domain = expression.AND([
                    args or [],
                    [('id', 'in', list(set(packaging_product_ids)))]
                ])
                packaging_search_ids = self._search(packaging_domain, limit=limit, order=order)
                # Merge all results
                all_ids = list(set(result + barcode_product_ids + packaging_search_ids))
                result = all_ids[:limit] if limit else all_ids
        
        return result
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override name_search to include packaging barcodes and store packaging info"""
        # First, perform the standard name search
        result = super(ProductProduct, self).name_search(name, args, operator, limit)
        result_ids = {r[0]: r[1] for r in result} if result else {}  # {id: display_name}
        
        # If name is provided, also search in packaging barcodes
        if name and len(name.strip()) > 0:
            name = name.strip()
            
            # Search in packaging barcodes
            packaging_domain = [('barcode', '=', name)]
            packagings = self.env['product.packaging'].search(packaging_domain)
            packaging_product_ids = []
            packaging_info_map = {}  # Store packaging info for each product
            
            if packagings:
                # Get product IDs from packagings
                for packaging in packagings:
                    if hasattr(packaging, 'product_id') and packaging.product_id:
                        product_id = packaging.product_id.id
                        packaging_product_ids.append(product_id)
                        # Store packaging info for this product
                        packaging_info_map[product_id] = {
                            'packaging_id': packaging.id,
                            'packaging_qty': packaging.qty,
                            'product_id': product_id
                        }
                    elif hasattr(packaging, 'product_tmpl_id') and packaging.product_tmpl_id:
                        # If only template is set, get all variants
                        variants = self.env['product.product'].search([
                            ('product_tmpl_id', '=', packaging.product_tmpl_id.id)
                        ])
                        for variant in variants:
                            packaging_product_ids.append(variant.id)
                            packaging_info_map[variant.id] = {
                                'packaging_id': packaging.id,
                                'packaging_qty': packaging.qty,
                                'product_id': variant.id
                            }
            
            # If we found products via packaging barcodes, add them to search results
            if packaging_product_ids:
                # Filter to only products that match the args domain
                packaging_domain = expression.AND([
                    args or [],
                    [('id', 'in', list(set(packaging_product_ids)))]
                ])
                packaging_search_ids = self._search(packaging_domain, limit=limit, order=None)
                
                # Get products found via packaging and add to results
                if packaging_search_ids:
                    packaging_products = self.browse(packaging_search_ids)
                    # Add packaging products to result dict
                    for product in packaging_products:
                        if product.id not in result_ids:
                            result_ids[product.id] = product.display_name
                    
                    # Store packaging info in cache for products found via packaging barcode
                    if not hasattr(self.env, '_packaging_search_cache'):
                        self.env._packaging_search_cache = {}
                    for product_id in packaging_search_ids:
                        if product_id in packaging_info_map:
                            self.env._packaging_search_cache[name] = packaging_info_map[product_id]
                            break  # Store first match
                
                # Convert back to list of tuples format
                result = [(pid, display_name) for pid, display_name in result_ids.items()]
                # Limit results
                result = result[:limit] if limit else result
        
        return result


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Override to set packaging and quantity when product is selected via packaging barcode"""
        # Call parent first
        super(StockMove, self)._onchange_product_id()
        
        # Check if product was selected via packaging barcode search
        # Look in the session cache for packaging info
        if self.product_id and hasattr(self.env, '_packaging_search_cache'):
            # Check all cached packaging searches to see if any match this product
            for barcode, packaging_info in self.env._packaging_search_cache.items():
                if packaging_info.get('product_id') == self.product_id.id:
                    packaging_id = packaging_info.get('packaging_id')
                    packaging_qty = packaging_info.get('packaging_qty')
                    
                    if packaging_id:
                        # Verify the packaging belongs to this product
                        packaging = self.env['product.packaging'].browse(packaging_id)
                        if packaging.exists() and packaging.product_id == self.product_id:
                            # Set the packaging
                            self.product_packaging_id = packaging.id
                            # Set the quantity to packaging contained quantity
                            if packaging_qty:
                                self.product_uom_qty = packaging_qty
                            # Clear the cache entry after use
                            del self.env._packaging_search_cache[barcode]
                            break


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Extend to include package_type_id field"""
        fields = super(ProductPackaging, self)._load_pos_data_fields(config_id)
        # Add package_type_id if it exists (from stock module)
        if 'package_type_id' in self._fields and 'package_type_id' not in fields:
            fields.append('package_type_id')
        return fields
    
    def _load_pos_data(self, data):
        """Override to ensure package_type_id is in [id, name] format"""
        result = super(ProductPackaging, self)._load_pos_data(data)
        # Ensure package_type_id is formatted as [id, name] for Many2one fields
        # result is a dict with 'data' key containing list of records
        if isinstance(result, dict) and 'data' in result:
            for record in result['data']:
                if 'package_type_id' in record and record['package_type_id']:
                    package_type_id = record['package_type_id']
                    # If it's just an ID, convert to [id, name] format
                    if isinstance(package_type_id, (int, float)):
                        package_type = self.env['stock.package.type'].browse(int(package_type_id))
                        if package_type.exists():
                            record['package_type_id'] = [package_type.id, package_type.name]
        return result


class PosSession(models.Model):
    _inherit = 'pos.session'

    def find_product_by_barcode(self, barcode, config_id):
        """
        Override to also search in packaging barcodes when doing text search.
        The original method already handles packaging for barcode scanning,
        but we extend it to also work with partial text searches.
        """
        result = super(PosSession, self).find_product_by_barcode(barcode, config_id)
        
        # If no product found and barcode looks like a search term (not exact match),
        # also search in packaging barcodes with ilike
        if not result.get('product.product') or len(result.get('product.product', [])) == 0:
            # Try searching with ilike for partial matches
            packaging = self.env['product.packaging'].search([
                ('barcode', 'ilike', barcode)
            ], limit=1)
            
            if packaging and packaging.product_id:
                product_fields = self.env['product.product']._load_pos_data_fields(config_id)
                product_packaging_fields = self.env['product.packaging']._load_pos_data_fields(config_id)
                product_context = {**self.env.context, 'display_default_code': False}
                
                product = packaging.product_id
                if product.sale_ok and product.available_in_pos:
                    return {
                        'product.product': product.with_context(product_context).read(product_fields, load=False),
                        'product.packaging': packaging.read(product_packaging_fields, load=False)
                    }
        
        return result

