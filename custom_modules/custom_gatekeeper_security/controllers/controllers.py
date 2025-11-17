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

    # Portal Card - Route
    @http.route(['/my/service_requests'], type='http', auth='user', website=True)
    def portal_service_requests(self, **kw):
        partner = request.env.user.partner_id
        sr_values = {
            'partner': partner,
            'company_name': partner.parent_id.name if partner.parent_id else "No Company",
            'service_address': "\n".join(filter(None, [partner.street, partner.street2])),
            'city': partner.city or '',
            'state_name': partner.state_id.name if partner.state_id else '',
            'zip_code': partner.zip or '',
            'primary_phone': partner.phone or partner.mobile or '',
            'email': partner.email or '',
            # Removed old partner.product_id (no longer exists)
        }
        return request.render('custom_gatekeeper_security.portal_service_request_form', sr_values)

    @http.route(['/my/service_requests/submit'], type='http', auth='user', website=True, csrf=True)
    def portal_service_request_submit(self, **post):
        partner = request.env.user.partner_id

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

        # Handle company selection
        company_name = post.get('company_partner_id')
        company_id = False
        if company_name:
            company_partner = request.env['res.partner'].sudo().search([('name', '=', company_name)], limit=1)
            company_id = company_partner.id if company_partner else False

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

        # Create the service request
        request.env['service.request'].sudo().create({
            'customer_id': partner.id,
            'company_partner_id': company_id,
            'preferred_contact_method': post.get('preferred_contact_method'),
            'requested_appointment': requested_appointment,
            'service_type_other_details': post.get('service_type_other_details'),
            'service_location': post.get('service_location'),
            'description': post.get('description'),
            'gate_code': post.get('gate_code'),
            'pets_on_site': post.get('pets_on_site') == 'on',
            'technician_notes': post.get('technician_notes'),
            'billing_address': post.get('billing_address'),
            'currency_id': currency_id,  # Explicitly set currency on service request
            'order_line': order_lines,
            'state': 'submitted',
        })

        return request.redirect('/my/service_requests/thankyou')

    # Thank You Page
    @http.route(['/my/service_requests/thankyou'], type='http', auth='user', website=True)
    def portal_service_request_thankyou(self, **kw):
        """Simple thank-you confirmation page"""
        return request.render('custom_gatekeeper_security.portal_service_request_thankyou')
