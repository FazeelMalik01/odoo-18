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
        name = post.get('name', '').strip()
        email = post.get('email', '').strip()
        password = post.get('password', '').strip()
        confirm_password = post.get('confirm_password', '').strip()

        # Validation
        errors = {}
        if not name:
            errors['name'] = 'Name is required'
        if not email:
            errors['email'] = 'Email is required'
        elif '@' not in email:
            errors['email'] = 'Invalid email format'
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

            # Create partner (dealer)
            partner = request.env['res.partner'].sudo().create({
                'name': name,
                'email': email,
                'is_company': False,
                'company_type': 'person',
            })

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
                'partner_id': partner.id,
                'active': False,  # Inactive until approved - prevents login
                'dealer_status': 'pending',  # Mark as pending dealer signup
                'show_customers_on_portal': False,  # Cards hidden until admin approves
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

            # Set dealer field on partner (dealer is themselves)
            partner.write({'dealer': partner.id})

            _logger.info(f"Created dealer user: {user.id}, Partner: {partner.id}")

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
            })
        except Exception as e:
            _logger.error(f"Error during dealer signup: {e}", exc_info=True)
            return request.render('custom_dealers_portal.dealer_signup_form', {
                'errors': {'general': 'An error occurred. Please try again or contact support.'},
                'name': name,
                'email': email,
            })
