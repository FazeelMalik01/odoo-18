from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
import json
import logging
import re
import html

_logger = logging.getLogger(__name__)


class purchaseorderformPortal(http.Controller):

    @http.route(['/my/purchase_orders'], type='http', auth='user', website=True)
    def portal_purchase_orders_list(self, **kw):
        """List sale orders created by the logged-in dealer from the portal."""
        dealer = request.env.user.partner_id

        sale_orders = request.env['sale.order'].sudo().search(
            [('dealer', '=', dealer.id)],
            order='date_order desc, id desc'
        )

        return request.render(
            'custom_dealers_portal.portal_purchase_orders_list',
            {
                'page_name': 'purchase_orders_list',
                'sale_orders': sale_orders,
                'dealer': dealer,
            }
        )

    def _render_form_with_error(self, error_message, dealer):
        """Helper method to render the form with an error message"""
        partner = dealer
        customers = request.env['res.partner'].sudo().search([
            ('dealer', '=', partner.id),
            ('is_company', '=', False),
        ])
        
        # Get products - filter by dealer's allowed categories if set
        dealer_user = request.env.user
        products = request.env['product.product'].sudo().browse([])
        if dealer_user.allowed_categories:
            product_domain = [
                ('sale_ok', '=', True),
                ('categ_id', 'in', dealer_user.allowed_categories.ids),
            ]
            products = request.env['product.product'].sudo().search(product_domain, limit=1000)
        
        # Format products with default_code display
        products_formatted = []
        for product in products:
            display_name = product.display_name or product.name
            products_formatted.append({
                'id': product.id,
                'name': product.name,
                'display_name': display_name,
                'categ_id': product.categ_id.id if product.categ_id else False,
                'categ_name': product.categ_id.name if product.categ_id else '',
                'uom_id': product.uom_id.id if product.uom_id else False,
            })
        
        # Get product categories - filter by dealer's allowed categories if set
        if dealer_user.allowed_categories:
            categories = dealer_user.allowed_categories
        else:
            categories = request.env['product.category'].sudo().browse([])
        
        # Check if dealer has show_catalog enabled
        show_catalog = dealer_user.show_catalog if hasattr(dealer_user, 'show_catalog') else False
        
        uoms = request.env['uom.uom'].sudo().search([])
        taxes = request.env['account.tax'].sudo().search([('type_tax_use', '=', 'sale')])
        
        return request.render(
            'custom_dealers_portal.portal_purchase_order_form',
            {
                'page_name': 'purchase_orders_form',
                'customers': customers,
                'products': products_formatted,
                'categories': categories,
                'uoms': uoms,
                'taxes': taxes,
                'order_name': '',
                'order_data': None,
                'is_readonly': False,
                'error': error_message,
                'show_catalog': show_catalog,
            }
        )

    @http.route(['/my/purchase_orders_form'], type='http', auth='user', website=True)
    def portal_purchase_order_form(self, order_id=None, view_mode=None, **kw):
        partner = request.env.user.partner_id
        customers = request.env['res.partner'].sudo().search([
            ('dealer', '=', partner.id),
            ('is_company', '=', False),
        ])
        
        # Get products with proper display name (including default_code)
        # Filter by dealer's allowed categories. If none are assigned, show no products.
        dealer_user = request.env.user
        products = request.env['product.product'].sudo().browse([])
        if dealer_user.allowed_categories:
            product_domain = [
                ('sale_ok', '=', True),
                ('categ_id', 'in', dealer_user.allowed_categories.ids),
            ]
            products = request.env['product.product'].sudo().search(product_domain, limit=1000)
        # Format products with default_code display
        # Use display_name which includes default_code in format [0001] Name
        products_formatted = []
        for product in products:
            # display_name is a computed field that includes default_code
            display_name = product.display_name or product.name
            products_formatted.append({
                'id': product.id,
                'name': product.name,
                'display_name': display_name,
                'categ_id': product.categ_id.id if product.categ_id else False,
                'categ_name': product.categ_id.name if product.categ_id else '',
                'uom_id': product.uom_id.id if product.uom_id else False,
            })
        
        # Get product categories - filter by dealer's allowed categories if set
        dealer_user = request.env.user
        if dealer_user.allowed_categories:
            # Only show categories that are in dealer's allowed_categories
            categories = dealer_user.allowed_categories
        else:
            categories = request.env['product.category'].sudo().browse([])
        
        uoms = request.env['uom.uom'].sudo().search([])
        taxes = request.env['account.tax'].sudo().search([('type_tax_use', '=', 'sale')])

        # Get order data if order_id passed
        order = None
        order_name = ''
        order_data = None
        # Existing orders open in readonly by default.
        is_readonly = bool(order_id)
        edit_mode = kw.get('edit_mode') or request.params.get('edit_mode')
        
        if order_id:
            order = request.env['sale.order'].sudo().browse(int(order_id))
            # Verify the order belongs to this dealer
            if order.exists() and order.dealer.id == partner.id:
                order_name = order.name
                # Dealers can edit only while waiting approval.
                can_edit_submitted = order.portal_state == 'to_be_approved'
                if edit_mode and can_edit_submitted:
                    is_readonly = False

                # Confirmed/cancelled portal statuses remain locked regardless of URL params.
                if order.portal_state in ('done', 'cancelled'):
                    is_readonly = True

                # Prepare order data for both readonly and edit rendering
                shipping_option_display = ''
                if order.shipping_option_dropship:
                    shipping_map = {
                        'rate_quote': 'Provide a rate quote before shipping',
                        'cheapest_rate': 'Please ship at cheapest rate',
                        'own_carrier': 'Client will use their own carrier',
                        'client_pickup': 'Client will pickup',
                        'yannick_pickup': 'Yannick will pickup this order',
                        'dhc_courier': 'Ship with DHC\'s courier and add cost to invoice',
                    }
                    shipping_option_display = shipping_map.get(order.shipping_option_dropship, '')

                order_data = {
                    'id': order.id,
                    'name': order.name,
                    'customer': order.partner_id.id,
                    'customer_name': order.partner_id.name,
                    'invoice_address': order.partner_invoice_id.id if order.partner_invoice_id else None,
                    'invoice_address_name': (order.partner_invoice_id.name_get()[0][1] if order.partner_invoice_id and order.partner_invoice_id.name_get() else '') or '',
                    'delivery_address': order.partner_shipping_id.id if order.partner_shipping_id else None,
                    'delivery_address_name': (order.partner_shipping_id.name_get()[0][1] if order.partner_shipping_id and order.partner_shipping_id.name_get() else '') or '',
                    'date_order': order.date_order.strftime('%Y-%m-%d %H:%M') if order.date_order else '',
                    'amount_total': order.amount_total,
                    'state': order.state,
                    'portal_state': order.portal_state,
                    'shipping_option_dropship': order.shipping_option_dropship or '',
                    'shipping_option_dropship_display': shipping_option_display,
                    'order_lines': []
                }
                # Get order lines
                for line in order.order_line:
                    line_taxes = []
                    tax_names = []

                    # Get taxes - check both tax_id and tax_ids fields
                    if hasattr(line, 'tax_id') and line.tax_id:
                        line_taxes = line.tax_id.ids
                        tax_names = [t.name for t in line.tax_id]
                    elif hasattr(line, 'tax_ids') and line.tax_ids:
                        line_taxes = line.tax_ids.ids
                        tax_names = [t.name for t in line.tax_ids]

                    # Get product display name with default_code
                    product_display_name = line.product_id.display_name or line.product_id.name

                    order_data['order_lines'].append({
                        'product_id': line.product_id.id,
                        'product_name': product_display_name,
                        'category_id': line.product_id.categ_id.id if line.product_id.categ_id else None,
                        'category_name': line.product_id.categ_id.name if line.product_id.categ_id else '',
                        'quantity': line.product_uom_qty,
                        'uom_id': line.product_uom_id.id if line.product_uom_id else None,
                        'uom_name': line.product_uom_id.name if line.product_uom_id else '',
                        'price_unit': line.price_unit,
                        'tax_ids': line_taxes,
                        'tax_names': tax_names,
                        'price_subtotal': line.price_subtotal,
                    })

        # Check if dealer has show_catalog enabled
        show_catalog = dealer_user.show_catalog if hasattr(dealer_user, 'show_catalog') else False
        
        return request.render(
            'custom_dealers_portal.portal_purchase_order_form',
            {
                'page_name': 'purchase_orders_form',
                'customers': customers,
                'products': products_formatted,
                'categories': categories,
                'uoms': uoms,
                'taxes': taxes,
                'order_name': order_name,
                'order_data': order_data,  # Changed from 'order' to avoid conflict with portal breadcrumb
                'is_readonly': is_readonly,
                'can_edit_submitted': bool(order and order.portal_state == 'to_be_approved'),
                'show_catalog': show_catalog,
            }
        )

    @http.route(['/my/purchase_orders_form/get_addresses'], type='json', auth='user', website=True, csrf=False)
    def get_addresses(self, customer_id=None, **kw):
        """Get invoice and delivery addresses for a customer (respect commercial partner).
        Invoice address should be from dealer, delivery address from customer."""
        # Handle JSON-RPC format if params are nested
        if 'params' in kw and isinstance(kw['params'], dict):
            customer_id = kw['params'].get('customer_id', customer_id)
        
        _logger.info(f"get_addresses called with customer_id: {customer_id}, kw: {kw}")
        
        if not customer_id:
            _logger.warning("No customer_id provided")
            return {'invoice_addresses': [], 'delivery_addresses': [], 'notes': ''}

        customer = request.env['res.partner'].sudo().browse(int(customer_id))
        if not customer.exists():
            _logger.warning(f"Customer {customer_id} does not exist")
            return {'invoice_addresses': [], 'delivery_addresses': [], 'notes': ''}
        
        _logger.info(f"Found customer: {customer.name} (ID: {customer.id})")

        # Get dealer from customer
        dealer = customer.dealer if customer.dealer else None
        
        # For invoice address: use dealer's invoice address
        invoice_addresses = []
        if dealer:
            # Work on the dealer's commercial partner
            dealer_base = dealer.commercial_partner_id or dealer
            invoice_addresses = [self._to_dict(dealer_base)]
            invoice_addrs = request.env['res.partner'].sudo().search([
                '|',
                ('commercial_partner_id', '=', dealer_base.id),
                ('parent_id', '=', dealer_base.id),
                ('type', '=', 'invoice'),
            ])
            for addr in invoice_addrs:
                if addr.id not in [a['id'] for a in invoice_addresses]:
                    invoice_addresses.append(self._to_dict(addr))
            if dealer.type == 'invoice' and dealer.id not in [a['id'] for a in invoice_addresses]:
                invoice_addresses.append(self._to_dict(dealer))
        else:
            # Fallback to customer if no dealer
            base_partner = customer.commercial_partner_id or customer
            invoice_addresses = [self._to_dict(base_partner)]
            invoice_addrs = request.env['res.partner'].sudo().search([
                '|',
                ('commercial_partner_id', '=', base_partner.id),
                ('parent_id', '=', base_partner.id),
                ('type', '=', 'invoice'),
            ])
            for addr in invoice_addrs:
                if addr.id not in [a['id'] for a in invoice_addresses]:
                    invoice_addresses.append(self._to_dict(addr))

        # For delivery address: use selected customer address (person) first.
        base_partner = customer

        # Get customer notes and strip HTML tags
        customer_notes = customer.comment or ''
        if customer_notes:
            # Strip HTML tags from comment field
            customer_notes = re.sub(r'<[^>]+>', '', customer_notes)
            # Decode HTML entities
            customer_notes = html.unescape(customer_notes)
            # Clean up extra whitespace
            customer_notes = ' '.join(customer_notes.split())
        
        # Get shipping option from customer
        shipping_option = customer.shipping_option_dropship or ''

        # Collect delivery addresses from selected customer hierarchy.
        delivery_addresses = [self._to_dict(base_partner)]
        delivery_addrs = request.env['res.partner'].sudo().search([
            '|',
            ('commercial_partner_id', '=', customer.commercial_partner_id.id),
            ('parent_id', '=', customer.id),
            ('type', '=', 'delivery'),
        ])
        _logger.info(f"Found {len(delivery_addrs)} delivery addresses for base_partner {base_partner.id}")
        for addr in delivery_addrs:
            if addr.id not in [a['id'] for a in delivery_addresses]:
                delivery_addresses.append(self._to_dict(addr))

        # If the selected contact is itself typed as delivery, ensure it is included
        if customer.type == 'delivery' and customer.id not in [a['id'] for a in delivery_addresses]:
            delivery_addresses.append(self._to_dict(customer))

        return {
            'invoice_addresses': invoice_addresses,
            'delivery_addresses': delivery_addresses,
            'notes': customer_notes,
            'shipping_option_dropship': shipping_option,
        }

    def _address_label(self, partner):
        """
        Build a stable, user-friendly label for dropdowns.
        Prefer showing the actual address (street/city/zip/...) instead of Odoo's
        display_name (which can be "Parent, Delivery/Invoice").
        """
        parts = []
        if partner.street:
            parts.append(partner.street)
        if getattr(partner, "street2", False) and partner.street2:
            parts.append(partner.street2)
        if partner.city:
            parts.append(partner.city)
        if getattr(partner, "state_id", False) and partner.state_id:
            parts.append(partner.state_id.name)
        if getattr(partner, "zip", False) and partner.zip:
            parts.append(partner.zip)
        if getattr(partner, "country_id", False) and partner.country_id:
            parts.append(partner.country_id.name)

        addr = ", ".join([p for p in parts if p])
        if addr:
            return addr

        # Fallbacks if no address is set
        return partner.name or partner.display_name or ''

    def _to_dict(self, partner):
        return {
            'id': partner.id,
            'name': partner.name,
            'display_name': partner.display_name or partner.name,
            'label': self._address_label(partner),
        }

    @http.route(['/my/purchase_orders_form/get_products_by_category'], type='json', auth='user', website=True, csrf=False)
    def get_products_by_category(self, category_id=None, **kw):
        """Get products filtered by category. If no category, return all products.
        Products are filtered to only include categories allowed for the dealer."""
        # Handle JSON-RPC format if params are nested
        if 'params' in kw and isinstance(kw['params'], dict):
            category_id = kw['params'].get('category_id', category_id)
        
        # Get dealer's allowed categories
        dealer_user = request.env.user
        allowed_category_ids = dealer_user.allowed_categories.ids if dealer_user.allowed_categories else []
        
        # Build domain for products
        domain = [('sale_ok', '=', True)]
        
        if category_id:
            # Filter products by specific category
            category_id_int = int(category_id)
            # Check if this category is allowed for the dealer
            if allowed_category_ids and category_id_int not in allowed_category_ids:
                # Category not allowed, return empty list
                return {'products': []}
            domain.append(('categ_id', '=', category_id_int))
        elif allowed_category_ids:
            # If dealer has allowed categories and no specific category selected,
            # only show products from allowed categories
            domain.append(('categ_id', 'in', allowed_category_ids))
        else:
            # No allowed categories: return no products.
            return {'products': []}
        
        products = request.env['product.product'].sudo().search(domain, limit=1000)
        
        # Format products with default_code display
        # Use display_name which includes default_code in format [0001] Name
        products_formatted = []
        for product in products:
            # display_name is a computed field that includes default_code
            display_name = product.display_name or product.name
            products_formatted.append({
                'id': product.id,
                'name': product.name,
                'display_name': display_name,
                'categ_id': product.categ_id.id if product.categ_id else False,
                'categ_name': product.categ_id.name if product.categ_id else '',
                'uom_id': product.uom_id.id if product.uom_id else False,
                'list_price': product.list_price or 0.0,
            })
        
        return {'products': products_formatted}

    @http.route(['/my/purchase_orders_form/get_product_info'], type='json', auth='user', website=True, csrf=False)
    def get_product_info(self, product_id=None, **kw):
        """Get product information including price and UOM"""
        if not product_id:
            return {}

        product = request.env['product.product'].sudo().browse(int(product_id))
        if not product.exists():
            return {}

        # Get tax information with rates
        taxes_data = []
        total_tax_rate = 0.0
        for tax in product.taxes_id:
            # Tax amount in Odoo is stored as percentage (e.g., 15 for 15%)
            tax_amount = tax.amount if hasattr(tax, 'amount') else 0.0
            # Convert to decimal for calculation (15 -> 0.15)
            tax_rate_decimal = tax_amount / 100.0
            total_tax_rate += tax_rate_decimal
            taxes_data.append({
                'id': tax.id,
                'name': tax.name,
                'amount': tax_amount,  # Keep as percentage for display
                'rate': tax_rate_decimal  # Decimal rate for calculation
            })

        return {
            'list_price': product.list_price,
            'uom_id': product.uom_id and [product.uom_id.id, product.uom_id.name] or False,
            'taxes': taxes_data,
            'total_tax_rate': total_tax_rate,
            # stock availability for portal display
            'qty_available': product.qty_available,
        }

    @http.route(['/my/purchase_orders_form/submit'], type='http', auth='user', website=True, methods=['POST'],
                csrf=True)
    def submit_purchase_order(self, **kw):
        """Submit purchase order form and create SALE order in Odoo"""
        try:
            dealer = request.env.user.partner_id

            # Get basic form data
            customer_id = kw.get('customer')
            if not customer_id:
                return self._render_form_with_error('Customer is required', dealer)

            # Get form data as MultiDict
            form_data = request.httprequest.form

            # Debug: Print all form data to see what we're receiving
            _logger.info("=== FORM DATA RECEIVED ===")
            for key, value in form_data.items():
                _logger.info(f"{key}: {value}")
            _logger.info("==========================")

            # Get product lines - try multiple formats
            product_ids = []

            # Method 1: Try array notation
            product_ids = form_data.getlist('product_ids[]')

            # Method 2: Try without brackets
            if not product_ids:
                product_ids = form_data.getlist('product_ids')

            # Method 3: Try as single value from kw
            if not product_ids and 'product_ids' in kw:
                product_id_value = kw.get('product_ids')
                if product_id_value:
                    if isinstance(product_id_value, list):
                        product_ids = product_id_value
                    else:
                        product_ids = [product_id_value]

            _logger.info(f"Product IDs found: {product_ids} (count: {len(product_ids)})")

            # If no product IDs found, try to extract them manually
            if not product_ids:
                # Try to find all product-related keys
                for key in form_data.keys():
                    if 'product' in key.lower():
                        values = form_data.getlist(key)
                        if values and values[0]:  # Check if not empty
                            product_ids.extend(values)
                            _logger.info(f"Found products in key '{key}': {values}")

            # Get quantities
            quantities = form_data.getlist('quantities[]')
            if not quantities:
                quantities = form_data.getlist('quantities')
            if not quantities and 'quantities' in kw:
                quantity_value = kw.get('quantities')
                if quantity_value:
                    if isinstance(quantity_value, list):
                        quantities = quantity_value
                    else:
                        quantities = [quantity_value]

            # Get UOMs
            uom_ids = form_data.getlist('uom_ids[]')
            if not uom_ids:
                uom_ids = form_data.getlist('uom_ids')
            if not uom_ids and 'uom_ids' in kw:
                uom_value = kw.get('uom_ids')
                if uom_value:
                    if isinstance(uom_value, list):
                        uom_ids = uom_value
                    else:
                        uom_ids = [uom_value]

            # Get prices
            price_units = form_data.getlist('price_units[]')
            if not price_units:
                price_units = form_data.getlist('price_units')
            if not price_units and 'price_units' in kw:
                price_value = kw.get('price_units')
                if price_value:
                    if isinstance(price_value, list):
                        price_units = price_value
                    else:
                        price_units = [price_value]

            # Prepare SALE order lines (matching Odoo sale.order.line structure)
            # Filter out empty rows - only process rows with valid product IDs
            order_lines = []
            line_taxes_map = []  # Store tax IDs for each order line (matching order_lines index)
            unavailable_products = []  # Collect products that are out of stock

            max_index = max(len(product_ids), len(quantities), len(uom_ids),
                            len(price_units)) if product_ids or quantities or uom_ids or price_units else 0

            for i in range(max_index):
                product_id = product_ids[i] if i < len(product_ids) else None

                # Skip rows without a product - these are empty rows
                if not product_id or str(product_id).strip() == '':
                    _logger.info(f"Skipping empty row at index {i} - no product selected")
                    continue

                quantity = quantities[i] if i < len(quantities) else '1'
                uom_id = uom_ids[i] if i < len(uom_ids) else ''
                price_unit = price_units[i] if i < len(price_units) else '0'

                # Stock availability check (server-side safety net)
                try:
                    product_rec = request.env['product.product'].sudo().browse(int(product_id))
                    requested_qty = float(quantity or 0.0)
                    if not product_rec.exists():
                        _logger.warning(f"Product ID {product_id} on line {i} does not exist; skipping.")
                        continue
                    if product_rec.qty_available < requested_qty or product_rec.qty_available <= 0:
                        unavailable_products.append(product_rec.display_name or product_rec.name or str(product_id))
                        _logger.info(
                            f"Line {i} blocked: product '{product_rec.display_name}' "
                            f"requested {requested_qty}, available {product_rec.qty_available}"
                        )
                        continue
                except Exception as availability_err:
                    _logger.error(f"Error checking stock for product {product_id} on line {i}: {availability_err}")
                    unavailable_products.append(str(product_id))
                    continue

                # Handle taxes from hidden inputs (comma-separated string or list)
                line_tax_ids = []

                # Method 1: Try array notation from form_data
                tax_hidden_list = form_data.getlist('tax_ids[]')
                if i < len(tax_hidden_list):
                    tax_hidden = tax_hidden_list[i]
                    if tax_hidden:
                        # Split comma-separated string
                        line_tax_ids = [int(tid) for tid in tax_hidden.split(',') if tid.strip()]

                # Method 2: Try from kw
                if not line_tax_ids:
                    # Try different key formats
                    tax_keys = [f'tax_ids[{i}]', f'tax_ids_{i}', f'tax_ids_{i}[]']
                    for tax_key in tax_keys:
                        if tax_key in kw:
                            tax_hidden = kw.get(tax_key)
                            if tax_hidden:
                                if isinstance(tax_hidden, str):
                                    line_tax_ids = [int(tid) for tid in tax_hidden.split(',') if tid.strip()]
                                elif isinstance(tax_hidden, list):
                                    line_tax_ids = [int(tid) for tid in tax_hidden if str(tid).strip()]
                                break

                # Also try getting all tax_ids and matching by index
                if not line_tax_ids:
                    all_tax_ids = form_data.getlist('tax_ids[]')
                    if not all_tax_ids:
                        all_tax_ids = form_data.getlist('tax_ids')

                    if i < len(all_tax_ids):
                        tax_hidden = all_tax_ids[i]
                        if tax_hidden:
                            line_tax_ids = [int(tid) for tid in tax_hidden.split(',') if tid.strip()]

                # Log what we found
                _logger.info(
                    f"Line {i}: product={product_id}, qty={quantity}, uom={uom_id}, price={price_unit}, taxes={line_tax_ids}")

                try:
                    # Create sale order line - using EXACT field names from sale.order.line
                    order_line_vals = {
                        'product_id': int(product_id),
                        'product_uom_qty': float(quantity),  # Sale order field name
                        'product_uom_id': int(uom_id) if uom_id and str(uom_id).strip() else False,
                        # Correct field name
                        'price_unit': float(price_unit),
                    }

                    # Don't set taxes here - we'll set them after order creation to avoid field name issues
                    # Store tax IDs to apply after order creation
                    order_lines.append((0, 0, order_line_vals))
                    line_taxes_map.append(line_tax_ids)  # Store taxes for this line

                    _logger.info(f"Successfully added sale order line {i} with taxes: {line_tax_ids}")

                except (ValueError, TypeError) as e:
                    _logger.warning(
                        f"Skipping line {i} due to error: {e}. Values: product={product_id}, qty={quantity}, uom={uom_id}, price={price_unit}")
                    continue

            # If any products are out of stock, block order creation and show error
            if unavailable_products:
                product_list = ', '.join(unavailable_products)
                return self._render_form_with_error(
                    f"The following products are out of stock or do not have enough quantity: {product_list}. "
                    f"Please adjust your order.",
                    dealer,
                )

            if not order_lines:
                _logger.error("No valid order lines created. Check form data submission.")
                _logger.error(f"Raw form data: {dict(form_data)}")
                _logger.error(f"Raw kw data: {kw}")
                return self._render_form_with_error(
                    'At least one valid order line is required. Please check that you have selected products.', dealer)

            customer_rec = request.env['res.partner'].sudo().browse(int(customer_id))
            dealer_base = (customer_rec.dealer.commercial_partner_id.id if customer_rec.dealer else False)

            # Get other addresses
            invoice_address_id = kw.get('invoice_address') or dealer_base or customer_id
            delivery_address_id = kw.get('delivery_address') or customer_id
            
            # Get shipping option from form or customer
            shipping_option = kw.get('shipping_option_dropship') or ''
            if not shipping_option:
                # Fallback to customer's shipping option
                if customer_rec.exists():
                    shipping_option = customer_rec.shipping_option_dropship or ''

            existing_order_id = kw.get('order_id')
            sale_order = None
            if existing_order_id:
                existing_order = request.env['sale.order'].sudo().browse(int(existing_order_id))
                if not existing_order.exists() or existing_order.dealer.id != dealer.id:
                    return self._render_form_with_error('Order not found or access denied.', dealer)
                if existing_order.portal_state != 'to_be_approved':
                    return self._render_form_with_error('This order can no longer be edited.', dealer)

                # Update existing submitted order
                existing_order.write({
                    'partner_id': int(customer_id),
                    'partner_invoice_id': int(invoice_address_id) if invoice_address_id else int(customer_id),
                    'partner_shipping_id': int(delivery_address_id) if delivery_address_id else int(customer_id),
                    'shipping_option_dropship': shipping_option or False,
                    'order_line': [(5, 0, 0)] + order_lines,
                })
                sale_order = existing_order
            else:
                # Create SALE order (this is what becomes the purchase order in Odoo backend)
                # New orders from the portal start in "To Be Approved" status
                sale_order = request.env['sale.order'].sudo().create({
                    'partner_id': int(customer_id),
                    'partner_invoice_id': int(invoice_address_id) if invoice_address_id else int(customer_id),
                    'partner_shipping_id': int(delivery_address_id) if delivery_address_id else int(customer_id),
                    'order_line': order_lines,
                    'dealer': dealer.id,  # Your custom field to track which dealer created this
                    'shipping_option_dropship': shipping_option or False,
                    'portal_state': 'to_be_approved',
                })

                # Notify backoffice/admin that a dealer submitted a portal quotation
                sale_order.action_notify_admin_portal_submission()

            # Update order lines with taxes separately (to avoid field name issues)
            # Use the stored tax IDs that match the order_lines
            for i, order_line in enumerate(sale_order.order_line):
                if i < len(line_taxes_map):
                    line_tax_ids = line_taxes_map[i]

                    # Update the order line with taxes if any
                    if line_tax_ids:
                        try:
                            # Try tax_id first (standard field name)
                            order_line.write({'tax_id': [(6, 0, line_tax_ids)]})
                            _logger.info(f"Updated order line {i} with taxes: {line_tax_ids}")
                        except Exception as e:
                            _logger.warning(f"Could not set taxes using tax_id on line {i}: {e}")

                            # Try alternative field name tax_ids (some Odoo versions use plural)
                            try:
                                order_line.write({'tax_ids': [(6, 0, line_tax_ids)]})
                                _logger.info(f"Updated order line {i} with taxes using tax_ids: {line_tax_ids}")
                            except Exception as e2:
                                _logger.error(f"Failed to set taxes on line {i} using both tax_id and tax_ids: {e2}")
                                # If both fail, taxes will use product defaults (not critical)

            _logger.info(f"Created sale order {sale_order.id} for customer {customer_id} with {len(order_lines)} lines")

            # Do NOT confirm or email here; leave in quotation state until backoffice approval.
            return request.redirect('/my/purchase_orders_form?success=1&order_id=%s' % sale_order.id)

        except Exception as e:
            _logger.error("Error creating sale order: %s", str(e), exc_info=True)
            dealer = request.env.user.partner_id
            return self._render_form_with_error(f'Error creating order: {str(e)}', dealer)
    
    @http.route(['/my/purchase_orders_form/catalog'], type='http', auth='user', website=True)
    def portal_catalog(self, **kw):
        """Display product catalog filtered by dealer's allowed categories"""
        dealer_user = request.env.user
        dealer_partner = dealer_user.partner_id
        dealer_pricelist = dealer_partner.property_product_pricelist

        # Check if catalog is enabled for this dealer
        if not hasattr(dealer_user, 'show_catalog') or not dealer_user.show_catalog:
            return request.redirect('/my/purchase_orders_form')
        
        # Get products filtered by allowed categories
        products = request.env['product.product'].sudo().browse([])
        if dealer_user.allowed_categories:
            product_domain = [('sale_ok', '=', True), ('categ_id', 'in', dealer_user.allowed_categories.ids)]
            products = request.env['product.product'].sudo().search(product_domain, limit=500)
        
        # Get categories for filtering
        if dealer_user.allowed_categories:
            categories = dealer_user.allowed_categories
        else:
            categories = request.env['product.category'].sudo().browse([])
        
        # Format products for display, including dealer-specific price and discount
        products_data = []
        for product in products:
            list_price = product.list_price or 0.0
            dealer_price = list_price
            discount_amount = 0.0
            discount_percent = 0.0

            if dealer_pricelist:
                try:
                    dealer_price = dealer_pricelist._get_product_price(product, quantity=1.0)
                    discount_amount = max(0.0, list_price - dealer_price)
                    discount_percent = (discount_amount / list_price * 100.0) if list_price else 0.0
                except Exception as price_err:
                    # Fallback gracefully to list price
                    _logger.warning(
                        "Error computing dealer price for product %s (%s): %s",
                        product.id, product.display_name, price_err,
                    )
                    dealer_price = list_price
                    discount_amount = 0.0
                    discount_percent = 0.0

            products_data.append({
                'id': product.id,
                'name': product.name,
                'display_name': product.display_name or product.name,
                'categ_id': product.categ_id.id if product.categ_id else False,
                'categ_name': product.categ_id.name if product.categ_id else '',
                'list_price': list_price,
                'dealer_price': dealer_price,
                'discount_amount': discount_amount,
                'discount_percent': discount_percent,
                'image_128': product.image_128 if hasattr(product, 'image_128') else False,
            })
        
        return request.render(
            'custom_dealers_portal.portal_product_catalog',
            {
                'page_name': 'product_catalog',
                'products': products_data,
                'categories': categories,
            }
        )
