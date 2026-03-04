# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class PortalServiceRequest(http.Controller):
    """
    Portal Controller for Service Requests
    """

    # List View - Route
    @http.route(['/my/service_requests', '/my/service_requests/page/<int:page>'], type='http', auth='user', website=True)
    def portal_service_requests_list(self, page=1, **kw):
        """List view of service requests for the current customer"""
        partner = request.env.user.partner_id
        
        # Search for service requests belonging to this customer
        ServiceRequest = request.env['service.request'].sudo()
        domain = [('customer_id', '=', partner.id)]
        
        # Pagination
        requests_per_page = 20
        total_requests = ServiceRequest.search_count(domain)
        pager = request.website.pager(
            url='/my/service_requests',
            total=total_requests,
            page=page,
            step=requests_per_page,
            scope=7
        )
        
        service_requests = ServiceRequest.search(
            domain,
            limit=requests_per_page,
            offset=(page - 1) * requests_per_page,
            order='create_date desc'
        )
        
        values = {
            'service_requests': service_requests,
            'pager': pager,
            'page_name': 'service_requests',
            'breadcrumb': [
                {'title': 'Home', 'url': '/my'},
                {'title': 'Service Requests', 'url': '/my/service_requests'}
            ],
        }
        
        return request.render('custom_gatekeeper_security.portal_service_request_list', values)

    # Form View - Route
    @http.route(['/my/service_requests/new'], type='http', auth='user', website=True)
    def portal_service_requests_form(self, **kw):
        """Form view for creating a new service request"""
        partner = request.env.user.partner_id
        # Fetch saleable products with sudo() to allow portal users to see them
        products = request.env['product.product'].sudo().search([('sale_ok', '=', True)])
        sr_values = {
            'partner': partner,
            'company_name': '',  # Empty initially
            'service_address': '',  # Empty initially
            'city': '',  # Empty initially
            'state_name': '',  # Empty initially
            'zip_code': '',  # Empty initially
            'primary_phone': '',  # Empty initially
            'email': partner.email or '',  # Pre-filled with partner email
            'products': products,  # Pass products to template
            'breadcrumb': [
                {'title': 'Home', 'url': '/my'},
                {'title': 'Service Requests', 'url': '/my/service_requests'},
                {'title': 'New Request', 'url': False}
            ],
            # Removed old partner.product_id (no longer exists)
        }
        return request.render('custom_gatekeeper_security.portal_service_request_form', sr_values)

    # Detail View - Route
    @http.route(['/my/service_requests/<int:request_id>'], type='http', auth='user', website=True)
    def portal_service_request_detail(self, request_id, **kw):
        """Detail view for a specific service request"""
        partner = request.env.user.partner_id
        
        # Verify the service request exists and belongs to this customer
        service_request = request.env['service.request'].sudo().search([
            ('id', '=', request_id),
            ('customer_id', '=', partner.id)
        ])
        
        if not service_request:
            return request.redirect('/my/service_requests')
        
        values = {
            'service_request': service_request,
            'page_name': 'service_request_detail',
            'breadcrumb': [
                {'title': 'Home', 'url': '/my'},
                {'title': 'Service Requests', 'url': '/my/service_requests'},
                {'title': service_request.name, 'url': False}
            ],
        }
        
        return request.render('custom_gatekeeper_security.portal_service_request_detail', values)

    @http.route(['/my/service_requests/submit'], type='http', auth='user', website=True, csrf=True)
    def portal_service_request_submit(self, **post):
        partner = request.env.user.partner_id

        # Handle service address
        service_address = post.get('service_address', '').strip()
        
        # Handle state - lookup by name (case-insensitive)
        state_id = False
        state_name = post.get('state_name', '').strip()
        if state_name:
            # Try exact match first
            state = request.env['res.country.state'].sudo().search([
                ('name', '=ilike', state_name)
            ], limit=1)
            if not state and partner.country_id:
                # Try with country restriction
                state = request.env['res.country.state'].sudo().search([
                    ('name', '=ilike', state_name),
                    ('country_id', '=', partner.country_id.id)
                ], limit=1)
            if state:
                state_id = state.id
                _logger.info("Found state: %s (ID: %s)", state_name, state_id)
            else:
                _logger.warning("State not found: %s (searched case-insensitively)", state_name)

        # Handle company - lookup by name (case-insensitive) or create if doesn't exist
        company_id = False
        company_name = post.get('company_partner_id', '').strip()
        if company_name and company_name != 'No Company' and company_name != 'N/A':
            # Try exact match first (case-insensitive)
            company_partner = request.env['res.partner'].sudo().search([
                ('name', '=ilike', company_name),
                ('is_company', '=', True)
            ], limit=1)
            if not company_partner:
                # Try without is_company filter
                company_partner = request.env['res.partner'].sudo().search([
                    ('name', '=ilike', company_name)
                ], limit=1)
            if company_partner:
                company_id = company_partner.id
                _logger.info("Found company: %s (ID: %s)", company_name, company_id)
            else:
                # Create company if it doesn't exist
                try:
                    company_partner = request.env['res.partner'].sudo().create({
                        'name': company_name,
                        'is_company': True,
                    })
                    company_id = company_partner.id
                    _logger.info("Created new company: %s (ID: %s)", company_name, company_id)
                except Exception as e:
                    _logger.error("Failed to create company %s: %s", company_name, str(e))

        # Convert requested_appointment safely
        requested_appointment = False
        requested_appointment_str = post.get('requested_appointment')
        if requested_appointment_str:
            try:
                requested_appointment = datetime.strptime(
                    requested_appointment_str.replace('T', ' '),
                    "%Y-%m-%d %H:%M"
                )
            except Exception as e:
                _logger.error("Error parsing requested_appointment: %s", e)
                requested_appointment = False

        # Get company currency for service request and order lines
        env_company = request.env.company
        currency_id = env_company.currency_id.id if env_company.currency_id else False
        
        # Handle product selection and create order lines
        order_lines = []
        product_id_str = post.get('product_id')
        if product_id_str:
            product = request.env['product.product'].sudo().browse(int(product_id_str))
            if product.exists():
                # Create order line with product details
                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': product.get_product_multiline_description_sale(),
                    'product_uom_id': product.uom_id.id,
                    'product_uom_qty': 1.0,
                    'price_unit': product.lst_price,
                    'tax_id': [(6, 0, product.taxes_id.filtered(lambda t: t.type_tax_use in ['sale', 'all']).ids)],
                    'currency_id': currency_id,  # Explicitly set currency
                }))

        # Prepare service request values - set computed fields directly
        service_request_vals = {
            'customer_id': partner.id,
            'preferred_contact_method': post.get('preferred_contact_method'),
            'requested_appointment': requested_appointment,
            'service_type_other_details': post.get('service_type_other_details'),
            'service_location': post.get('service_location'),
            'description': post.get('description'),
            'gate_code': post.get('gate_code'),
            'pets_on_site': post.get('pets_on_site') == 'on',
            'technician_notes': post.get('technician_notes'),
            'billing_address': post.get('billing_address'),
            'currency_id': currency_id,
            'order_line': order_lines,
            'state': 'submitted',
        }
        
        # Set service address if provided
        if service_address:
            service_request_vals['service_address'] = service_address
        
        # Set state_id if found
        if state_id:
            service_request_vals['state_id'] = state_id
        
        # Set company_partner_id if found
        if company_id:
            service_request_vals['company_partner_id'] = company_id

        # Create the service request with manually set values
        service_request = request.env['service.request'].sudo().create(service_request_vals)
        
        # After create, ensure manually set values are preserved (write again to override any compute)
        write_vals = {}
        if service_address:
            write_vals['service_address'] = service_address
        if state_id:
            write_vals['state_id'] = state_id
        if company_id:
            write_vals['company_partner_id'] = company_id
        
        if write_vals:
            service_request.sudo().write(write_vals)

        return request.redirect('/my/service_requests/thankyou')

    # Thank You Page
    @http.route(['/my/service_requests/thankyou'], type='http', auth='user', website=True)
    def portal_service_request_thankyou(self, **kw):
        """Simple thank-you confirmation page"""
        values = {
            'breadcrumb': [
                {'title': 'Home', 'url': '/my'},
                {'title': 'Service Requests', 'url': '/my/service_requests'},
                {'title': 'Thank You', 'url': False}
            ],
        }
        return request.render('custom_gatekeeper_security.portal_service_request_thankyou', values)
