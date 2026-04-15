from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class DealerSignup(http.Controller):

    @http.route('/dealers/signup', type='http', auth='public', website=True)
    def dealer_signup_page(self, **kw):
        """Display dealer signup form"""
        return request.render('custom_dealers_portal.dealer_signup_form', {})

    @http.route('/dealers/signup/submit', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def dealer_signup_submit(self, **post):
        """Handle dealer signup form submission"""
        # Contact person details
        name = post.get('name', '').strip()
        email = post.get('email', '').strip()
        phone = post.get('phone', '').strip()

        # Company details
        company_name = post.get('company_name', '').strip()
        company_address = post.get('company_address', '').strip()

        # Extra questionnaire-style fields
        connection_to_company = post.get('connection_to_company', '').strip()
        business_description = post.get('business_description', '').strip()

        # Account password (for portal user created in pending state)
        password = post.get('password', '').strip()
        confirm_password = post.get('confirm_password', '').strip()

        # Validation
        allowed_connections = {'owner', 'route_driver', 'employee', 'technician', 'buyer'}
        errors = {}
        if not name:
            errors['name'] = 'Name is required'
        if not email:
            errors['email'] = 'Email is required'
        elif '@' not in email:
            errors['email'] = 'Invalid email format'
        if not phone:
            errors['phone'] = 'Phone number is required'
        if not company_name:
            errors['company_name'] = 'Company name is required'
        if not company_address:
            errors['company_address'] = 'Company address is required'
        if not connection_to_company:
            errors['connection_to_company'] = 'Please select your connection to the company'
        elif connection_to_company not in allowed_connections:
            errors['connection_to_company'] = 'Invalid connection type selected'
        if not business_description:
            errors['business_description'] = 'Please describe how you can help your clients'
        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        if password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match'

        if errors:
            return request.render('custom_dealers_portal.dealer_signup_form', {
                'errors': errors,
                'name': name,
                'email': email,
                'phone': phone,
                'company_name': company_name,
                'company_address': company_address,
                'connection_to_company': connection_to_company,
                'business_description': business_description,
            })

        try:
            # Check if user with this email already exists
            existing_user = request.env['res.users'].sudo().search([
                ('login', '=', email)
            ], limit=1)

            if existing_user:
                return request.render('custom_dealers_portal.dealer_signup_form', {
                    'errors': {'email': 'An account with this email already exists'},
                    'name': name,
                    'email': email,
                })

            # Create company partner
            company_partner = request.env['res.partner'].sudo().create({
                'name': company_name,
                'street': company_address,
                'is_company': True,
                'company_type': 'company',
            })

            # Create contact person under the company
            contact_partner = request.env['res.partner'].sudo().create({
                'name': name,
                'email': email,
                'phone': phone,
                'mobile_number': phone,
                'parent_id': company_partner.id,
                'is_company': False,
                'company_type': 'person',
            })

            # Mark the company partner itself as a dealer (used by portal flows)
            company_partner.write({'dealer': company_partner.id})

            # Create a CRM lead capturing the application details
            try:
                description_lines = [
                    f"Connection to company: {connection_to_company}",
                    "",
                    "How they can help clients:",
                    business_description,
                ]
                request.env['crm.lead'].sudo().create({
                    'name': f"Dealer Application - {company_name}",
                    'partner_id': company_partner.id,
                    'partner_name': company_name,
                    'contact_name': name,
                    'email_from': email,
                    'phone': phone,
                    'description': "\n".join(description_lines),
                    'type': 'lead',
                })
            except Exception as e:
                # Lead creation should not block signup; log and continue
                _logger.warning("Could not create CRM lead for dealer signup: %s", e, exc_info=True)

            # Get portal group first
            portal_group = request.env.ref('base.group_portal', raise_if_not_found=False)
            if not portal_group:
                raise ValidationError("Portal group not found. Please check module installation.")
            
            # Create user first without groups (groups_id cannot be set during create)
            user = request.env['res.users'].sudo().with_context(no_reset_password=True).create({
                'name': name,
                'login': email,
                'email': email,
                'password': password,
                'partner_id': contact_partner.id,
                'active': False,  # Inactive until approved - prevents login
                'dealer_status': 'pending',  # Mark as pending dealer signup
                'show_customers_on_portal': False,  # Cards hidden until admin approves
                'dealer_connection_to_company': connection_to_company,
                'dealer_business_description': business_description,
                'dealer_company_name': company_name,
                'dealer_company_address': company_address,
            })
            
            # Assign portal group after creation using direct SQL (more reliable)
            # First, remove any existing groups
            request.env.cr.execute("""
                DELETE FROM res_groups_users_rel WHERE uid = %s
            """, (user.id,))
            
            # Then add the portal group
            request.env.cr.execute("""
                INSERT INTO res_groups_users_rel (gid, uid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (portal_group.id, user.id))
            
            # Invalidate cache to ensure fresh data (without specifying fields to avoid errors)
            try:
                user.invalidate_recordset()
            except Exception as e:
                _logger.warning(f"Could not invalidate cache for user {user.id}: {e}")

            _logger.info(f"Created dealer user: {user.id}, Company Partner: {company_partner.id}, Contact Partner: {contact_partner.id}")

            # Commit the transaction
            request.env.cr.commit()

            # Redirect to login with success message
            return request.redirect('/web/login?signup=success')

        except ValidationError as e:
            _logger.error(f"Validation error during dealer signup: {e}")
            return request.render('custom_dealers_portal.dealer_signup_form', {
                'errors': {'general': str(e)},
                'name': name,
                'email': email,
                'phone': phone,
                'company_name': company_name,
                'company_address': company_address,
                'connection_to_company': connection_to_company,
                'business_description': business_description,
            })
        except Exception as e:
            _logger.error(f"Error during dealer signup: {e}", exc_info=True)
            return request.render('custom_dealers_portal.dealer_signup_form', {
                'errors': {'general': 'An error occurred. Please try again or contact support.'},
                'name': name,
                'email': email,
                'phone': phone,
                'company_name': company_name,
                'company_address': company_address,
                'connection_to_company': connection_to_company,
                'business_description': business_description,
            })
