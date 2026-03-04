from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessDenied
import logging

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = "res.users"
    
    @api.model
    def _register_hook(self):
        """Clean up any old views/filters that reference dealer_signup_pending"""
        super()._register_hook()
        try:
            # Remove any filters that reference the old field
            old_filters = self.env['ir.filters'].sudo().search([
                ('model_id', '=', 'res.users'),
                ('domain', 'ilike', 'dealer_signup_pending')
            ])
            if old_filters:
                _logger.info(f"Removing {len(old_filters)} old filters referencing dealer_signup_pending")
                old_filters.unlink()
            
            # Update any views that might reference the old field
            # This is handled by the view inheritance, but we can force a refresh
            self.env['ir.ui.view'].sudo().invalidate_cache(['arch_db'])
            
            # Auto-approve all existing admins
            admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
            if admin_group:
                admin_users = self.env['res.users'].sudo().search([
                    ('groups_id', 'in', [admin_group.id]),
                    ('dealer_status', '!=', 'approved')
                ])
                if admin_users:
                    _logger.info(f"Auto-approving {len(admin_users)} admin users")
                    admin_users.write({'dealer_status': 'approved', 'active': True})
        except Exception as e:
            _logger.warning(f"Error in _register_hook: {e}")

    show_customers_on_portal = fields.Boolean(
        string="Show Customers on Portal",
        default=False,
        store=True,
        help="When enabled, the user will see Customers and Purchase Orders cards on the portal. Only admin can set this."
    )

    dealer_status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('approved', 'Approved'),
        ],
        string='Dealer Status',
        default='pending',
        store=True,
        help="Status of dealer signup. Pending dealers need approval."
    )

    has_dealer_group = fields.Boolean(
        string="Has Dealer Group",
        compute="_compute_has_dealer_group",
        store=False,
        readonly=True,
        help="Shows if user has the Dealer group assigned. Automatically managed based on dealer status."
    )
    
    allowed_categories = fields.Many2many(
        'product.category',
        'dealer_allowed_categories_rel',
        'user_id',
        'category_id',
        string='Allowed Categories',
        help='Product categories that this dealer can access on the portal. If empty, all categories are allowed.',
        groups="base.group_system"
    )
    
    show_catalog = fields.Boolean(
        string="Show Catalog",
        default=False,
        store=True,
        help="When enabled, dealer will see a Catalog button on the purchase order form to browse products."
    )

    def _compute_has_dealer_group(self):
        """Check if user has dealer group assigned"""
        dealer_group = self.env.ref('custom_dealers_portal.group_dealer', raise_if_not_found=False)
        for user in self:
            if dealer_group:
                # Use has_group method which is the standard Odoo way to check groups
                user.has_dealer_group = user.has_group('custom_dealers_portal.group_dealer')
            else:
                user.has_dealer_group = False
    
    @api.model
    def _setup_base(self):
        """Override to handle migration from dealer_signup_pending to dealer_status"""
        super()._setup_base()
        # This ensures the field is properly registered even if there are cached views
        if 'dealer_status' not in self._fields:
            # Field should already be defined, but this is a safety check
            pass
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle dealer_status"""
        users = super().create(vals_list)
        for user in users:
            # Admins are always approved and should have dealer group if they need it
            if user.has_group('base.group_system'):
                if user.dealer_status != 'approved':
                    user.dealer_status = 'approved'
                # Ensure admin has dealer group
                dealer_group = self.env.ref('custom_dealers_portal.group_dealer', raise_if_not_found=False)
                if dealer_group and not user.has_group('custom_dealers_portal.group_dealer'):
                    try:
                        if 'groups_id' in user._fields:
                            user.write({'groups_id': [(4, dealer_group.id)]})
                        else:
                            self.env.cr.execute("""
                                INSERT INTO res_groups_users_rel (gid, uid)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                            """, (dealer_group.id, user.id))
                    except Exception as e:
                        _logger.warning(f"Could not assign dealer group to admin {user.id}: {e}")
            elif user.dealer_status == 'approved':
                user._ensure_dealer_group()
        return users
    
    def write(self, vals):
        """Override write to automatically manage dealer group based on status"""
        # Store info before write to avoid recursion
        dealer_status_changed = 'dealer_status' in vals
        new_status = vals.get('dealer_status')
        user_ids = list(self.ids) if dealer_status_changed else []
        
        result = super().write(vals)
        
        # After write, check if any user is an admin and auto-approve them
        for user in self:
            if user.has_group('base.group_system'):
                # Admins are always approved
                if user.dealer_status != 'approved':
                    user.sudo().write({'dealer_status': 'approved'})
                    new_status = 'approved'
                    dealer_status_changed = True
                    if user.id not in user_ids:
                        user_ids.append(user.id)
                
                # Ensure admin has dealer group
                dealer_group = self.env.ref('custom_dealers_portal.group_dealer', raise_if_not_found=False)
                if dealer_group and not user.has_group('custom_dealers_portal.group_dealer'):
                    try:
                        if 'groups_id' in user._fields:
                            user.write({'groups_id': [(4, dealer_group.id)]})
                        else:
                            self.env.cr.execute("""
                                INSERT INTO res_groups_users_rel (gid, uid)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                            """, (dealer_group.id, user.id))
                    except Exception as e:
                        _logger.warning(f"Could not assign dealer group to admin {user.id}: {e}")
        
        # Handle group assignment and activation after write to avoid recursion
        if dealer_status_changed and user_ids:
            self._post_write_manage_dealer_group(user_ids, new_status)
            # Activate user when approved, but don't deactivate admins
            if new_status == 'approved':
                self.browse(user_ids).sudo().write({'active': True})
            elif new_status == 'pending':
                # Don't deactivate admins
                for user_id in user_ids:
                    user = self.browse(user_id)
                    if not user.has_group('base.group_system'):
                        user.sudo().write({'active': False})
        
        return result
    
    def _post_write_manage_dealer_group(self, user_ids, new_status):
        """Manage dealer group assignment after write to avoid recursion"""
        dealer_group = self.env.ref('custom_dealers_portal.group_dealer', raise_if_not_found=False)
        if not dealer_group:
            return
        
        # Use a completely fresh environment to avoid any context issues
        fresh_env = self.env(user=self.env.user.id)
        users = fresh_env['res.users'].sudo().browse(user_ids)
        
        for user in users:
            has_group = user.has_group('custom_dealers_portal.group_dealer')
            try:
                if new_status == 'approved' and not has_group:
                    # Check if groups_id field exists before writing
                    if 'groups_id' in user._fields:
                        user.write({'groups_id': [(4, dealer_group.id)]})
                    else:
                        # Fallback: use direct SQL if field not accessible
                        self.env.cr.execute("""
                            INSERT INTO res_groups_users_rel (gid, uid)
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING
                        """, (dealer_group.id, user.id))
                        self.env.cr.commit()
                        user.invalidate_recordset()
                elif new_status == 'pending' and has_group:
                    if 'groups_id' in user._fields:
                        user.write({'groups_id': [(3, dealer_group.id)]})
                    else:
                        # Fallback: use direct SQL if field not accessible
                        self.env.cr.execute("""
                            DELETE FROM res_groups_users_rel
                            WHERE gid = %s AND uid = %s
                        """, (dealer_group.id, user.id))
                        self.env.cr.commit()
                        user.invalidate_recordset()
            except Exception as e:
                _logger.warning(f"Could not update dealer group for user {user.id}: {e}")
    
    def approve_dealer(self):
        """Approve dealer - assign dealer group and set status to approved"""
        dealer_group = self.env.ref('custom_dealers_portal.group_dealer', raise_if_not_found=False)
        if not dealer_group:
            raise ValidationError("Dealer group not found. Please check module installation.")
        
        for user in self:
            # Set status to approved - this will trigger write() which assigns the group and activates user
            user.write({'dealer_status': 'approved'})
        
        return True
    
    def _check_credentials(self, password, user_agent=None):
        """Override to prevent pending dealers from logging in"""
        result = super()._check_credentials(password, user_agent)
        
        # Admins can always log in, even if they're marked as pending
        if self.has_group('base.group_system'):
            return result
        
        # Check if user is a pending dealer (non-admins only)
        if hasattr(self, 'dealer_status') and self.dealer_status == 'pending':
            raise AccessDenied("Your dealer account is pending approval. Please wait for admin approval before logging in.")
        
        return result