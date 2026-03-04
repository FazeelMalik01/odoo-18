from odoo import models, fields, api, exceptions
import re


class ResPartner(models.Model):
    _inherit = 'res.partner'

    email_other = fields.Char(string='Email Other')
    email_home = fields.Char(string='Email Home')
    phone_home = fields.Char(string='Phone Home')
    mobile_number = fields.Char(string='Mobile Number')
    other_phone = fields.Char(string='Other Phone')

    person_salutation = fields.Selection(
        selection=[
            ('mr', 'Mr.'),
            ('mrs', 'Mrs.'),
            ('ms', 'Ms.'),
            ('dr', 'Dr.')
        ],
        string='Salutation'
    )
    person_occupation = fields.Selection(
        selection=[
            ('professional hoof trimmer', 'Professional Hoof Trimmer'),
            ('veterinarian', 'Veterinarian'),
            ('farrier for horses', 'Farrier for horses'),
            ('sheep shearer', 'Sheep Shearer'),
            ('nutritionist', 'Nutritionist'),
            ('researcher', 'Researcher'),
            ('dairy farmer', 'Dairy farmer'),
            ('farm product sales', 'Farm product sales'),
            ('farm service business', 'Farm Service Business'),
            ('sheep farmer', 'Sheep farmer'),
            ('horse owner', 'Horse owner'),
            ('hog farmer', 'Hog farmer'),
            ('none', 'None of the above'),
        ],
        string='Occupation'
    )
    occupation_notes = fields.Text(string='Occupation Notes')
    lead_source = fields.Selection([
        ('trade_show_meeting', 'Trade Show meeting'),
        ('phone_call_inbound', 'Phone Call inbound'),
        ('email_inbound', 'Email inbound'),
        ('form_website', 'Form on our Website'),
        ('intracare', 'Received from Intracare'),
        ('word_of_mouth', 'Word of Mouth'),
        ('farmer_referral', 'Farmer Referral'),
        ('vet_referral', 'Vet Referral'),
        ('linkedin_outreach', 'LinkedIn Outreach'),
        ('industry_publication', 'Industry Publication follow-up'),
    ], string='Lead Source')
    
    # New checkbox field for multiple contact types
    contact_type_ids = fields.Many2many(
        'contact.type',
        'partner_contact_type_rel',
        'partner_id', 'contact_type_id',
        string='Contact Types'
    )
    
    # GLN field for delivery contacts
    global_location_number = fields.Char(string="GLN", help="Global Location Number")
    
    # Computed fields for visibility logic
    show_delivery_fields = fields.Boolean(
        compute='_compute_field_visibility', 
        string='Show Delivery Fields',
        help='Show address and GLN fields when Receiving Contact is selected'
    )
    show_invoice_fields = fields.Boolean(
        compute='_compute_field_visibility', 
        string='Show Invoice Fields'
    )
    show_contact_fields = fields.Boolean(
        compute='_compute_field_visibility', 
        string='Show Contact Fields'
    )
    show_other_fields = fields.Boolean(
        compute='_compute_field_visibility', 
        string='Show Other Fields'
    )
    show_sale_fields = fields.Boolean(
        compute='_compute_field_visibility', 
        string='Show Sale Fields'
    )
    is_only_contact = fields.Boolean(
        compute='_compute_field_visibility',
        string='Is Only Contact',
        help='True when only Main Contact is selected (hide address fields)'
    )
    
    # Keep original type field for backward compatibility
    type = fields.Selection(selection_add=[
        ('contact', 'Main Contact'),
        ('invoice', 'Accounting Contact'),
        ('delivery', 'Receiving Contact'),
        ('sale_contact', 'Sale Contact'),
        ('shipping_cc', 'Shipping Cc'),
        ('accounting_cc', 'Accounting Cc'),
        ('marketing', 'Marketing Contact'),
        ('other', 'Other'),
    ])
    google_drive = fields.Char(string='Google Drive')
    qbo_profile = fields.Char(string='QBO Profile')
    
    # Shipping Address fields (for companies only)
    shipping_street = fields.Char(string='Shipping Street')
    shipping_street2 = fields.Char(string='Shipping Street 2')
    shipping_city = fields.Char(string='Shipping City')
    shipping_state_id = fields.Many2one(
        'res.country.state',
        string='Shipping State',
        domain="[('country_id', '=', shipping_country_id)]"
    )
    shipping_zip = fields.Char(string='Shipping ZIP')
    shipping_country_id = fields.Many2one('res.country', string='Shipping Country')

    @api.depends('contact_type_ids.code')
    def _compute_field_visibility(self):
        """Compute visibility of fields based on selected contact types - matches original radio button behavior"""
        for partner in self:
            # Get codes from checkbox selections
            selected_codes = partner.contact_type_ids.mapped('code')
            
            # Match original radio button logic exactly
            # Contact = Main Contact (show person fields, hide address)
            partner.show_contact_fields = 'contact' in selected_codes
            
            # Invoice = Accounting Contact (show invoice fields)
            partner.show_invoice_fields = 'invoice' in selected_codes
            
            # Delivery = Receiving Contact (show address fields and GLN)
            partner.show_delivery_fields = 'delivery' in selected_codes
            
            # Sale Contact (show sales fields)
            partner.show_sale_fields = 'sale_contact' in selected_codes
            
            # Other = Other (show all other fields)
            partner.show_other_fields = 'other' in selected_codes
            
            # Is only contact: True when only 'contact' is selected (hide address fields)
            partner.is_only_contact = (
                'contact' in selected_codes and 
                len(partner.contact_type_ids) == 1
            )


    @api.model
    def format_phone_number(self, phone):
        """Format phone number to standard format: (XXX) XXX-XXXX"""
        if not phone:
            return ''
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Handle different length scenarios
        if len(digits) == 10:
            # Standard 10-digit US number
            area_code = digits[:3]
            prefix = digits[3:6]
            line_number = digits[6:]
            return f'({area_code}) {prefix}-{line_number}'
        elif len(digits) == 11 and digits[0] == '1':
            # US number with country code
            area_code = digits[1:4]
            prefix = digits[4:7]
            line_number = digits[7:]
            return f'({area_code}) {prefix}-{line_number}'
        elif len(digits) >= 7:
            # At least 7 digits (XXX-XXXX format)
            if len(digits) == 7:
                return f'{digits[:3]}-{digits[3:]}'
            else:
                # More than 10 digits, return as is but cleaned
                return digits
        else:
            # Less than 7 digits, return as is but cleaned
            return digits

    @api.model
    def validate_phone_number(self, phone):
        """Validate phone number format"""
        if not phone:
            return True
        
        # Remove all non-digit characters for validation
        digits = re.sub(r'\D', '', phone)
        
        # Accept 7-digit (local), 10-digit (standard), or 11-digit (with country code)
        if len(digits) in [7, 10, 11]:
            return True
        
        return False

    def write(self, vals):
        """Override write to format phone numbers"""
        phone_fields = ['phone', 'phone_home', 'mobile_number', 'other_phone']
        
        for field in phone_fields:
            if field in vals and vals[field]:
                # Validate phone number
                if not self.validate_phone_number(vals[field]):
                    raise exceptions.ValidationError(f'Invalid phone number format for {field}. Please enter a valid phone number ex-(XXX) XXX-XXXX.')
                
                # Format phone number
                vals[field] = self.format_phone_number(vals[field])
        
        return super().write(vals)

    def create(self, vals):
        """Override create to format phone numbers and sync type field"""
        phone_fields = ['phone', 'phone_home', 'mobile_number', 'other_phone']
        
        for field in phone_fields:
            if field in vals and vals[field]:
                # Validate phone number
                if not self.validate_phone_number(vals[field]):
                    raise exceptions.ValidationError(f'Invalid phone number format for {field}. Please enter a valid phone number ex-(XXX) XXX-XXXX.')
                
                # Format phone number
                vals[field] = self.format_phone_number(vals[field])
        
        # Sync type field based on contact_type_ids if not explicitly set
        if 'contact_type_ids' in vals and 'type' not in vals:
            vals = self._sync_type_from_contact_types(vals)
        
        result = super().create(vals)
        
        # After creation, ensure type is synced if contact_type_ids was set
        if 'contact_type_ids' in vals:
            result._sync_type_from_contact_types_after_write()
        
        return result

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        """Override to prevent automatic address inheritance from parent to child contacts.
        This allows child contacts to have fully independent addresses."""
        # Don't copy address from parent - allow independent addresses
        # Only sync company_id and other non-address fields if needed
        if not self.parent_id:
            return {}
        result = {}
        # Only sync company_id, not addresses
        if self.parent_id.company_id:
            result['value'] = {'company_id': self.parent_id.company_id.id}
        return result

    def _fields_sync(self, values):
        """Override to prevent address syncing from parent to child contacts.
        This ensures child contacts maintain independent addresses."""
        # Store original address values before parent sync (if this is a child contact)
        address_fields = self._address_fields()
        original_addresses = {}
        is_child_contact = bool(self.parent_id)
        
        # If this is a child contact, save current address values to prevent inheritance
        if is_child_contact:
            for field in address_fields:
                # If address field is in values, it's being explicitly set - keep it
                if field in values:
                    original_addresses[field] = values[field]
                # If address field already has a value, keep it
                elif self[field]:
                    original_addresses[field] = self[field]
        
        # Call parent method for commercial fields and other syncs
        # The parent will try to sync addresses, but we'll restore them afterward
        result = super()._fields_sync(values)
        
        # Restore original addresses to prevent any address inheritance
        # This ensures child contacts maintain fully independent addresses
        if original_addresses and is_child_contact:
            for field in address_fields:
                if field in original_addresses:
                    # Always restore original address values (prevents parent address inheritance)
                    self[field] = original_addresses[field]
        
        return result

    def _children_sync(self, values):
        """Override to prevent address syncing from parent to children.
        This ensures child contacts maintain independent addresses."""
        # Don't sync address fields to children - they should be independent
        address_fields = self._address_fields()
        if any(field in values for field in address_fields):
            # Skip address syncing to children
            # Only sync commercial fields
            if self.commercial_partner_id == self:
                fields_to_sync = values.keys() & self._commercial_fields()
                self.sudo()._commercial_sync_to_descendants(fields_to_sync)
        else:
            # For non-address fields, use parent behavior
            super()._children_sync(values)

    def address_get(self, adr_pref=None):
        """Override to use custom contact types for address lookup.
        Maps custom contact types to standard Odoo address types:
        - Accounting Contact (code='invoice') -> 'invoice'
        - Receiving Contact (code='delivery') -> 'delivery'
        - Main Contact (code='contact') -> 'contact'
        """
        adr_pref = set(adr_pref or [])
        if 'contact' not in adr_pref:
            adr_pref.add('contact')
        result = {}
        visited = set()
        
        for partner in self:
            current_partner = partner
            while current_partner:
                to_scan = [current_partner]
                # Scan descendants, DFS
                while to_scan:
                    record = to_scan.pop(0)
                    visited.add(record)
                    
                    # Check if this record matches any requested address type
                    # First check the type field (for backward compatibility)
                    if record.type in adr_pref and not result.get(record.type):
                        result[record.type] = record.id
                    
                    # Also check custom contact types
                    # Map custom contact types to standard address types
                    contact_codes = record.contact_type_ids.mapped('code')
                    
                    # Map 'invoice' contact type to 'invoice' address type
                    if 'invoice' in adr_pref and 'invoice' in contact_codes and not result.get('invoice'):
                        result['invoice'] = record.id
                    
                    # Map 'delivery' contact type to 'delivery' address type
                    if 'delivery' in adr_pref and 'delivery' in contact_codes and not result.get('delivery'):
                        result['delivery'] = record.id
                    
                    # Map 'contact' contact type to 'contact' address type
                    if 'contact' in adr_pref and 'contact' in contact_codes and not result.get('contact'):
                        result['contact'] = record.id
                    
                    if len(result) == len(adr_pref):
                        return result
                    
                    to_scan = [c for c in record.child_ids
                                 if c not in visited
                                 if not c.is_company] + to_scan

                # Continue scanning at ancestor if current_partner is not a commercial entity
                if current_partner.is_company or not current_partner.parent_id:
                    break
                current_partner = current_partner.parent_id

        # default to type 'contact' or the partner itself
        default = result.get('contact', self.id or False)
        for adr_type in adr_pref:
            result[adr_type] = result.get(adr_type) or default
        return result

    def _sync_type_from_contact_types(self, vals):
        """Helper method to sync type field based on contact_type_ids during create.
        This ensures backward compatibility with address_get() method.
        Priority: invoice > delivery > contact > other"""
        if 'contact_type_ids' not in vals or 'type' in vals:
            return vals
        
        # Get contact type codes from Command format
        if isinstance(vals['contact_type_ids'], list):
            contact_type_commands = vals['contact_type_ids']
            contact_type_ids = []
            
            for cmd in contact_type_commands:
                if isinstance(cmd, (list, tuple)) and len(cmd) >= 2:
                    if cmd[0] == 6:  # Command.SET
                        contact_type_ids = cmd[2] if len(cmd) > 2 else []
                    elif cmd[0] == 4:  # Command.LINK
                        contact_type_ids.append(cmd[1])
                    elif cmd[0] == 5:  # Command.UNLINK_ALL
                        contact_type_ids = []
            
            if contact_type_ids:
                contact_types = self.env['contact.type'].browse(contact_type_ids)
                codes = contact_types.mapped('code')
            else:
                codes = []
        else:
            return vals
        
        # Set type based on priority: invoice > delivery > contact
        if 'invoice' in codes:
            vals['type'] = 'invoice'
        elif 'delivery' in codes:
            vals['type'] = 'delivery'
        elif 'contact' in codes:
            vals['type'] = 'contact'
        elif codes:
            # Use first code as fallback
            vals['type'] = codes[0] if codes[0] in ['sale_contact', 'shipping_cc', 'accounting_cc', 'marketing', 'other'] else 'contact'
        else:
            # No contact types selected, default to contact
            vals['type'] = 'contact'
        
        return vals

    def _sync_type_from_contact_types_after_write(self):
        """Sync type field after write based on current contact_type_ids.
        This ensures backward compatibility with address_get() method."""
        for partner in self:
            codes = partner.contact_type_ids.mapped('code')
            
            # Set type based on priority: invoice > delivery > contact
            if 'invoice' in codes:
                partner.type = 'invoice'
            elif 'delivery' in codes:
                partner.type = 'delivery'
            elif 'contact' in codes:
                partner.type = 'contact'
            elif codes:
                # Use first code as fallback
                partner.type = codes[0] if codes[0] in ['sale_contact', 'shipping_cc', 'accounting_cc', 'marketing', 'other'] else 'contact'
            else:
                # No contact types selected, default to contact
                partner.type = 'contact'

    @api.onchange('contact_type_ids')
    def _onchange_contact_type_ids(self):
        """Onchange to sync type field when contact_type_ids changes.
        This ensures backward compatibility with address_get() method."""
        if not self.contact_type_ids:
            self.type = 'contact'
            return
        
        codes = self.contact_type_ids.mapped('code')
        
        # Set type based on priority: invoice > delivery > contact
        if 'invoice' in codes:
            self.type = 'invoice'
        elif 'delivery' in codes:
            self.type = 'delivery'
        elif 'contact' in codes:
            self.type = 'contact'
        elif codes:
            # Use first code as fallback
            self.type = codes[0] if codes[0] in ['sale_contact', 'shipping_cc', 'accounting_cc', 'marketing', 'other'] else 'contact'
        else:
            # No contact types selected, default to contact
            self.type = 'contact'

    @api.onchange('phone')
    def _onchange_phone(self):
        """Format phone number in real-time as user types"""
        if self.phone:
            digits = re.sub(r'\D', '', self.phone)
            if len(digits) >= 10:
                self.phone = self.format_phone_number(self.phone)

    @api.onchange('phone_home')
    def _onchange_phone_home(self):
        """Format phone_home number in real-time as user types"""
        if self.phone_home:
            digits = re.sub(r'\D', '', self.phone_home)
            if len(digits) >= 10:
                self.phone_home = self.format_phone_number(self.phone_home)

    @api.onchange('mobile_number')
    def _onchange_mobile_number(self):
        """Format mobile_number in real-time as user types"""
        if self.mobile_number:
            digits = re.sub(r'\D', '', self.mobile_number)
            if len(digits) >= 10:
                self.mobile_number = self.format_phone_number(self.mobile_number)

    @api.onchange('other_phone')
    def _onchange_other_phone(self):
        """Format other_phone number in real-time as user types"""
        if self.other_phone:
            digits = re.sub(r'\D', '', self.other_phone)
            if len(digits) >= 10:
                self.other_phone = self.format_phone_number(self.other_phone)

    def write(self, vals):
        """Override write to format phone numbers and sync type field"""
        phone_fields = ['phone', 'phone_home', 'mobile_number', 'other_phone']
        
        for field in phone_fields:
            if field in vals and vals[field]:
                # Validate phone number
                if not self.validate_phone_number(vals[field]):
                    raise exceptions.ValidationError(f'Invalid phone number format for {field}. Please enter a valid phone number ex-(XXX) XXX-XXXX.')
                
                # Format phone number
                vals[field] = self.format_phone_number(vals[field])
        
        # Sync type field based on contact_type_ids if contact_type_ids is being updated
        if 'contact_type_ids' in vals and 'type' not in vals:
            # We'll sync after write to ensure contact_type_ids is properly set
            pass
        
        result = super().write(vals)
        
        # After write, sync type field if contact_type_ids was updated
        if 'contact_type_ids' in vals:
            self._sync_type_from_contact_types_after_write()
        
        return result
