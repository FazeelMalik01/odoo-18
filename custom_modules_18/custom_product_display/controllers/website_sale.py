# -*- coding: utf-8 -*-

from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from werkzeug.utils import redirect


class WebsiteSaleInherit(WebsiteSale):
    """Override website sale controller to filter out empty categories and out-of-stock products"""

    @http.route()
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        """Override shop method to filter categories and products"""
        res = super(WebsiteSaleInherit, self).shop(
            page=page, category=category, search=search, ppg=ppg, **post
        )
        
        # Check if the current category has no stocked products
        # If it's a subcategory without products, redirect to parent or shop
        if 'category' in res.qcontext and res.qcontext['category']:
            current_category = res.qcontext['category']
            # Compute has_stocked_products for the current category
            if not current_category.has_stocked_products:
                # Category has no stock, redirect to parent or shop
                if current_category.parent_id:
                    # Redirect to parent category if it exists
                    parent_category = current_category.parent_id
                    if parent_category.has_stocked_products:
                        # Redirect to parent category
                        return redirect(
                            '/shop/category/%s' % parent_category.id, code=302
                        )
                    else:
                        # Parent also has no stock, redirect to shop
                        return redirect('/shop', code=302)
                else:
                    # No parent, redirect to shop
                    return redirect('/shop', code=302)
        
        # Filter categories to only show those with stocked products
        # Check all possible category-related context variables
        category_keys = ['categories', 'category', 'category_id']
        for key in category_keys:
            if key in res.qcontext:
                categories = res.qcontext[key]
                if categories:
                    if isinstance(categories, list):
                        # If it's a list, filter it
                        res.qcontext[key] = [c for c in categories if hasattr(c, 'has_stocked_products') and c.has_stocked_products]
                    elif hasattr(categories, 'filtered'):
                        # If it's a recordset, filter it
                        res.qcontext[key] = categories.filtered(lambda c: c.has_stocked_products)
        
        # Filter child categories for the main category if it exists
        # This ensures subcategories without stock are not displayed
        if 'category' in res.qcontext and res.qcontext['category']:
            main_category = res.qcontext['category']
            # Ensure has_stocked_products is computed for the category and its children
            if main_category:
                # Compute for main category
                _ = main_category.has_stocked_products
                # Compute for all children and filter them
                if main_category.child_id:
                    # Compute has_stocked_products for all children first
                    # This ensures the computation runs for all children
                    children_with_stock = []
                    for child in main_category.child_id:
                        # Force computation
                        _ = child.has_stocked_products
                        # Only add if it has stock
                        if child.has_stocked_products:
                            children_with_stock.append(child.id)
                    
                    # Store filtered children IDs in context
                    res.qcontext['filtered_category_children_ids'] = children_with_stock
                    # Also store the filtered recordset
                    filtered_children = main_category.child_id.browse(children_with_stock)
                    res.qcontext['filtered_category_children'] = filtered_children
        
        # Filter products to only show those with stock
        # Check all possible product-related keys in qcontext
        product_keys = ['products', 'search_product', 'product_ids', 'product']
        for key in product_keys:
            if key in res.qcontext:
                products = res.qcontext[key]
                if products:
                    try:
                        if isinstance(products, list):
                            # If it's a list, filter it
                            filtered_list = []
                            for p in products:
                                if hasattr(p, '_has_stock'):
                                    try:
                                        if p._has_stock():
                                            filtered_list.append(p)
                                    except Exception:
                                        # If _has_stock fails, include the product to be safe
                                        filtered_list.append(p)
                                else:
                                    # If _has_stock doesn't exist, include the product
                                    filtered_list.append(p)
                            res.qcontext[key] = filtered_list
                        elif hasattr(products, 'filtered'):
                            # If it's a recordset, filter it
                            try:
                                filtered_products = products.filtered(lambda p: p._has_stock() if hasattr(p, '_has_stock') else True)
                                res.qcontext[key] = filtered_products
                            except Exception:
                                # If filtering fails, don't filter (show all products)
                                pass
                    except Exception:
                        # If there's any error, don't filter (show all products to avoid breaking the page)
                        pass
        
        return res

    def _shop_lookup_products(self, attrib_set, options, post, search, website):
        """Override to filter products after lookup"""
        result = super(WebsiteSaleInherit, self)._shop_lookup_products(
            attrib_set, options, post, search, website
        )
        
        # Based on Odoo 18 source, the return is: (fuzzy_search_term, product_count, search_product)
        if isinstance(result, tuple) and len(result) == 3:
            fuzzy_search_term, product_count, search_product = result
            
            # Filter products to only show those with stock
            if search_product and hasattr(search_product, 'filtered'):
                try:
                    search_product = search_product.filtered(lambda p: p._has_stock() if hasattr(p, '_has_stock') else True)
                    product_count = len(search_product)
                except Exception:
                    # If filtering fails, don't filter (show all products)
                    pass
            
            return fuzzy_search_term, product_count, search_product
        
        # If format is unexpected, return as-is
        return result

    def _get_search_domain(self, search='', category='', attrib_values=None, **kwargs):
        """Override to add stock filter to product search"""
        domain = super(WebsiteSaleInherit, self)._get_search_domain(
            search=search, category=category, attrib_values=attrib_values, **kwargs
        )
        
        # Don't add qty_available filter here as it requires warehouse access
        # Products will be filtered after search in the shop() method
        return domain
