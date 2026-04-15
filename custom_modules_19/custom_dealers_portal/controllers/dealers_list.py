from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied
import logging
import re
import html
import json

_logger = logging.getLogger(__name__)


class DealerPortal(http.Controller):

    def _strip_html(self, text):
        """Strip HTML tags from text"""
        if not text:
            return ''
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = html.unescape(text)
        # Clean up extra whitespace
        return ' '.join(text.split())

    @http.route('/my/customers_list', type='http', auth='user', website=True)
    def portal_customers_list(self, **kw):
        partner = request.env.user.partner_id

        customers = request.env['res.partner'].sudo().search([
            ('dealer', '=', partner.id),
            ('is_company', '=', False),
        ])

        return request.render(
            'custom_dealers_portal.portal_customers_list',
            {
                'page_name': 'customers_list',
                'customers': customers,
            }
        )

    @http.route('/my/add_customer', type='http', auth='user', methods=['POST'], csrf=False, website=True)
    def portal_add_customer(self, **post):
        """Add a new customer"""
        try:
            # Parse JSON from request body
            if request.httprequest.content_type == 'application/json':
                post = json.loads(request.httprequest.data.decode('utf-8'))
            
            _logger.info(f"Add customer called with data: {post}")

            name = post.get('name')
            if not name:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Customer name is required'}),
                    headers=[('Content-Type', 'application/json')]
                )

            dealer = request.env.user.partner_id
            has_customer_company = str(post.get('has_customer_company', '')).lower() in ('1', 'true', 'yes', 'on')
            customer_company_name = (post.get('customer_company_name') or '').strip()
            customer_company_address = (post.get('customer_company_address') or '').strip()

            if has_customer_company and not customer_company_name:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Company name is required when customer has a company'}),
                    headers=[('Content-Type', 'application/json')]
                )
            if has_customer_company and not customer_company_address:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Company address is required when customer has a company'}),
                    headers=[('Content-Type', 'application/json')]
                )

            parent_id = dealer.id
            if has_customer_company:
                company_partner = request.env['res.partner'].sudo().create({
                    'name': customer_company_name,
                    'street': customer_company_address,
                    'is_company': True,
                    'company_type': 'company',
                    'dealer': dealer.id,
                })
                parent_id = company_partner.id

            customer = request.env['res.partner'].sudo().create({
                'name': name,
                'email': post.get('email'),
                'phone': post.get('phone'),
                'dealer': dealer.id,
                'mobile_number': post.get('mobile_number'),
                'comment': post.get('comment'),
                'shipping_option_dropship': post.get('shipping_option_dropship') or False,
                'company_type': 'person',
                'parent_id': parent_id,
                'type': 'contact',
                'has_customer_company': has_customer_company,
                'customer_company_name': customer_company_name if has_customer_company else False,
                'customer_company_address': customer_company_address if has_customer_company else False,
            })

            _logger.info(f"Created customer ID: {customer.id}, Name: {customer.name}")
            return request.make_response(
                json.dumps({'success': True, 'customer_id': customer.id}),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error(f"Error creating customer: {e}")
            return request.make_response(
                json.dumps({'success': False, 'error': str(e)}),
                headers=[('Content-Type', 'application/json')]
            )

    @http.route('/my/update_customer', type='http', auth='user', methods=['POST'], csrf=False, website=True)
    def portal_update_customer(self, **post):
        """Update customer information"""
        try:
            # Parse JSON from request body
            content_type = request.httprequest.content_type or ''
            if 'application/json' in content_type:
                try:
                    post = json.loads(request.httprequest.data.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    _logger.error(f"Error parsing JSON: {e}")
                    return request.make_response(
                        json.dumps({'success': False, 'error': 'Invalid JSON format'}),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )
            
            _logger.info(f"Update customer called with data: {post}")

            customer_id = post.get('customer_id')
            if not customer_id:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Customer ID is required'}),
                    headers=[('Content-Type', 'application/json')]
                )

            dealer = request.env.user.partner_id

            # First, let's check if the customer exists and belongs to this dealer
            customer = request.env['res.partner'].sudo().search([
                ('id', '=', int(customer_id)),
                ('dealer', '=', dealer.id),
                ('is_company', '=', False),
            ], limit=1)

            _logger.info(f"Customer search result: {customer}")
            _logger.info(f"Customer ID to update: {customer_id}")
            _logger.info(f"Dealer ID: {dealer.id}")

            if not customer:
                # Let's check all customers of this dealer to debug
                all_customers = request.env['res.partner'].sudo().search([
                    ('dealer', '=', dealer.id)
                ])
                _logger.info(f"All customers for dealer {dealer.id}: {all_customers.mapped('id')}")
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Customer not found or access denied'}),
                    headers=[('Content-Type', 'application/json')]
                )

            update_vals = {}
            if 'name' in post and post['name']:
                update_vals['name'] = post.get('name')
                _logger.info(f"Updating name to: {post.get('name')}")
            if 'email' in post:
                update_vals['email'] = post.get('email')
                _logger.info(f"Updating email to: {post.get('email')}")
            if 'phone' in post:
                update_vals['phone'] = post.get('phone')
                _logger.info(f"Updating phone to: {post.get('phone')}")
            if 'mobile_number' in post:
                update_vals['mobile_number'] = post.get('mobile_number')
                _logger.info(f"Updating mobile_number to: {post.get('mobile_number')}")
            if 'comment' in post:
                update_vals['comment'] = post.get('comment')
                _logger.info(f"Updating comment to: {post.get('comment')}")
            if 'shipping_option_dropship' in post:
                update_vals['shipping_option_dropship'] = post.get('shipping_option_dropship') or False
                _logger.info(f"Updating shipping_option_dropship to: {post.get('shipping_option_dropship')}")
            has_customer_company = str(post.get('has_customer_company', '')).lower() in ('1', 'true', 'yes', 'on')
            customer_company_name = (post.get('customer_company_name') or '').strip()
            customer_company_address = (post.get('customer_company_address') or '').strip()

            if has_customer_company and not customer_company_name:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Company name is required when customer has a company'}),
                    headers=[('Content-Type', 'application/json')]
                )
            if has_customer_company and not customer_company_address:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Company address is required when customer has a company'}),
                    headers=[('Content-Type', 'application/json')]
                )

            update_vals['has_customer_company'] = has_customer_company
            update_vals['customer_company_name'] = customer_company_name if has_customer_company else False
            update_vals['customer_company_address'] = customer_company_address if has_customer_company else False

            # Keep person parent hierarchy aligned with company/dealer selection.
            if has_customer_company:
                company_partner = customer.parent_id if customer.parent_id and customer.parent_id != dealer else None
                if company_partner:
                    company_partner.write({
                        'name': customer_company_name,
                        'street': customer_company_address,
                        'dealer': dealer.id,
                    })
                else:
                    company_partner = request.env['res.partner'].sudo().create({
                        'name': customer_company_name,
                        'street': customer_company_address,
                        'is_company': True,
                        'company_type': 'company',
                        'dealer': dealer.id,
                    })
                update_vals['parent_id'] = company_partner.id
            else:
                update_vals['parent_id'] = dealer.id

            _logger.info(f"Update values: {update_vals}")

            if update_vals:
                customer.write(update_vals)
                # Commit the changes
                request.env.cr.commit()
                # Invalidate cache to ensure fresh data
                customer.invalidate_recordset()
                _logger.info(f"After update - Name: {customer.name}, Email: {customer.email}, Phone: {customer.phone}")

            return request.make_response(
                json.dumps({'success': True}),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error(f"Error updating customer: {e}")
            return request.make_response(
                json.dumps({'success': False, 'error': str(e)}),
                headers=[('Content-Type', 'application/json')]
            )

    @http.route('/my/delete_customer', type='http', auth='user', methods=['POST'], csrf=False, website=True)
    def portal_delete_customer(self, **post):
        """Delete a customer"""
        try:
            # Parse JSON from request body
            if request.httprequest.content_type == 'application/json':
                post = json.loads(request.httprequest.data.decode('utf-8'))
            
            _logger.info(f"Delete customer called with data: {post}")

            customer_id = post.get('customer_id')
            if not customer_id:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Customer ID is required'}),
                    headers=[('Content-Type', 'application/json')]
                )

            dealer = request.env.user.partner_id

            customer = request.env['res.partner'].sudo().search([
                ('id', '=', int(customer_id)),
                ('dealer', '=', dealer.id),
                ('is_company', '=', False),
            ], limit=1)

            if not customer:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Customer not found or access denied'}),
                    headers=[('Content-Type', 'application/json')]
                )

            customer_id = customer.id
            customer.unlink()
            # Commit the deletion
            request.env.cr.commit()
            _logger.info(f"Deleted customer ID: {customer_id}")

            return request.make_response(
                json.dumps({'success': True}),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error(f"Error deleting customer: {e}")
            return request.make_response(
                json.dumps({'success': False, 'error': str(e)}),
                headers=[('Content-Type', 'application/json')]
            )
