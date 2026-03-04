from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError


class LaundryAppointment(models.Model):
    _name = 'laundry.appointment'
    _description = 'Laundry Service Appointment'
    _order = 'appointment_date desc, appointment_time desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Appointment Reference', required=True, copy=False, readonly=True, 
                      default=lambda self: 'New')
    
    customer_name = fields.Char(string='Customer Name', required=True, tracking=True)
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone', required=False, tracking=True)
    zip_code = fields.Char(string='Zip Code', tracking=True)
    service_type_ids = fields.Many2many( 
        'product.product', 
        'laundry_appointment_product_product_rel',
        'appointment_id', 
        'product_id',
        string='Service Types', 
        required=True,
        tracking=True,
        domain=[('type', '=', 'service')]
    )
    
    # Appointment Type Integration (Odoo's appointment module)
    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='Appointment Type',
        default=lambda self: self._get_default_appointment_type(),
        help='The appointment type configuration (e.g., Meeting) that defines available time slots'
    )
    time_slot_id = fields.Many2one(
        'appointment.slot',
        string='Time Slot',
        help='The specific time slot selected from the appointment type configuration'
    )
    
    appointment_date = fields.Date(string='Appointment Date', required=True, tracking=True)
    appointment_time = fields.Char(
        string='Appointment Time', 
        compute='_compute_appointment_time',
        store=True,
        tracking=True,
        help='Computed from the selected time slot'
    )
    
    # Booking tracking
    booking_id = fields.Many2one(
        'laundry.appointment.booking',
        string='Slot Booking',
        readonly=True,
        help='The booking record that reserves this time slot'
    )
    
    notes = fields.Text(string='Notes / Special Instructions')
    
    pickup_address = fields.Text(string='Pickup Address', help='Address where items will be picked up')
    delivery_address = fields.Text(string='Delivery Address', help='Address where items will be delivered')
    pickup_city = fields.Char(string='Pickup City', help='City for pickup address')
    pickup_state_id = fields.Many2one('res.country.state', string='Pickup State/Province', help='State or Province for pickup address', domain="[('country_id', '=', pickup_country_id)]")
    pickup_country_id = fields.Many2one('res.country', string='Pickup Country', help='Country for pickup address')
    
    status = fields.Selection([
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('pickup', 'Pickup'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delivery', 'Delivery'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', tracking=True)
    
    partner_id = fields.Many2one('res.partner', string='Partner', 
                                 default=lambda self: self.env.user.partner_id if self.env.user.partner_id else False)
    user_id = fields.Many2one('res.users', string='User', 
                              default=lambda self: self.env.user, readonly=True)
    
    # Partner who confirmed/claimed this service request
    assigned_partner_id = fields.Many2one('res.partner', string='Assigned Partner', 
                                          help='Partner who confirmed and claimed this service request')
    
    # User responses
    user_response_ids = fields.One2many(
        'laundry.appointment.user.response',
        'appointment_id',
        string='User Responses'
    )
    
    # Sales Order link
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True)
    sale_order_count = fields.Integer(string='Sales Order Count', compute='_compute_sale_order_count')
    
    date_time_display = fields.Char(string='Date & Time', compute='_compute_date_time_display', store=False)

    # Completion images - stored as attachments
    completion_image_count = fields.Integer(
        string='Completion Images Count',
        compute='_compute_completion_image_count',
        help='Number of images uploaded when service is completed'
    )
    
    completion_image_ids = fields.Many2many(
        'ir.attachment',
        string='Completion Images',
        compute='_compute_completion_image_ids',
        readonly=True,
        store=False
    )
    
    def _compute_completion_image_count(self):
        """Compute the count of completion images"""
        for record in self:
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'laundry.appointment'),
                ('res_id', '=', record.id),
                ('res_field', '=', 'completion_images')
            ])
            record.completion_image_count = len(attachments)
    
    def _compute_completion_image_ids(self):
        """Compute the completion images attachments"""
        for record in self:
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'laundry.appointment'),
                ('res_id', '=', record.id),
                ('res_field', '=', 'completion_images')
            ])
            record.completion_image_ids = [(6, 0, attachments.ids)]
    
    def get_completion_images(self):
        """Get completion images for this appointment"""
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'laundry.appointment'),
            ('res_id', '=', self.id),
            ('res_field', '=', 'completion_images')
        ])
        return attachments

    @api.depends('sale_order_id')
    def _compute_sale_order_count(self):
        """Compute the number of sales orders linked to this appointment"""
        for record in self:
            record.sale_order_count = 1 if record.sale_order_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate name based on customer and date"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                customer_name = vals.get('customer_name', 'Customer')
                appointment_date = vals.get('appointment_date', '')
                if appointment_date:
                    # Format: CustomerName - YYYY-MM-DD
                    date_str = str(appointment_date)
                    vals['name'] = f"{customer_name} - {date_str}"
                else:
                    vals['name'] = f"{customer_name} - Appointment"
        return super(LaundryAppointment, self).create(vals_list)
    
    @api.depends('appointment_date', 'appointment_time')
    def _compute_date_time_display(self):
        """Compute formatted date and time for display"""
        for record in self:
            if record.appointment_date and record.appointment_time:
                try:
                    date_obj = record.appointment_date
                    formatted_date = date_obj.strftime('%B %d, %Y')
                    # Parse time string (HH:MM format)
                    time_str = record.appointment_time
                    if ':' in time_str:
                        hour, minute = time_str.split(':')
                        hour_int = int(hour)
                        am_pm = 'AM' if hour_int < 12 else 'PM'
                        if hour_int == 0:
                            hour_int = 12
                        elif hour_int > 12:
                            hour_int -= 12
                        formatted_time = f"{hour_int}:{minute} {am_pm}"
                    else:
                        formatted_time = time_str
                    record.date_time_display = f"{formatted_date} {formatted_time}"
                except:
                    record.date_time_display = f"{record.appointment_date} {record.appointment_time}"
            else:
                record.date_time_display = ''
    
    def name_get(self):
        """Custom display name"""
        result = []
        for record in self:
            name = f"{record.name} - {record.customer_name}"
            result.append((record.id, name))
        return result
    
    def action_create_sale_order(self):
        """Create a sales order from service request"""
        self.ensure_one()
        
        # Validate partner exists
        if not self.partner_id:
            raise UserError('Please set a Partner before creating a sales order.')
        
        # Validate service types exist
        if not self.service_type_ids:
            raise UserError('Please add at least one service type before creating a sales order.')
        
        # Prepare order lines from service types
        order_lines = []
        for product in self.service_type_ids:
            order_lines.append((0, 0, {
                'product_id': product.id,
                'name': product.name,
                'product_uom_qty': 1.0,
                'price_unit': product.list_price,
            }))
        
        # Create sales order
        # Convert appointment date to datetime if available
        date_order = fields.Datetime.now()
        if self.appointment_date:
            # Combine date and time if both are available
            try:
                if self.appointment_time:
                    # Parse time (format: HH:MM or HH:MM AM/PM)
                    time_str = self.appointment_time.strip()
                    if 'AM' in time_str.upper() or 'PM' in time_str.upper():
                        # Handle 12-hour format
                        from datetime import datetime as dt
                        time_obj = dt.strptime(time_str, '%I:%M %p').time()
                    else:
                        # Handle 24-hour format
                        from datetime import datetime as dt
                        time_obj = dt.strptime(time_str, '%H:%M').time()
                    date_order = fields.Datetime.to_datetime(f"{self.appointment_date} {time_obj}")
                else:
                    date_order = fields.Datetime.to_datetime(self.appointment_date)
            except:
                date_order = fields.Datetime.to_datetime(self.appointment_date)
        
        sale_order_vals = {
            'partner_id': self.partner_id.id if self.partner_id else False,
            'date_order': date_order,
            'order_line': order_lines,
            'note': f"Service Request: {self.name}\nCustomer: {self.customer_name}\nPhone: {self.phone}\nEmail: {self.email or 'N/A'}\nAppointment Date: {self.appointment_date} {self.appointment_time or ''}\n\nNotes: {self.notes or 'N/A'}",
        }
        
        sale_order = self.env['sale.order'].create(sale_order_vals)
        
        # Link the sales order to this appointment
        self.write({'sale_order_id': sale_order.id})
        
        # Automatically confirm the sales order (change from Quotation to Sales Order)
        sale_order.action_confirm()
        
        # Return action to open the sales order form
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_sale_order(self):
        """Open the sales order form view from smart button"""
        self.ensure_one()
        
        if not self.sale_order_id:
            return {'type': 'ir.actions.act_window_close'}
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _get_default_appointment_type(self):
        """Get the default appointment type (Meeting)"""
        # Try to find 'Meeting' appointment type
        appointment_type = self.env['appointment.type'].search([
            ('name', 'ilike', 'meeting')
        ], limit=1)
        return appointment_type.id if appointment_type else False
    
    @api.depends('time_slot_id', 'time_slot_id.start_hour', 'time_slot_id.end_hour')
    @api.depends('time_slot_id', 'booking_id', 'booking_id.slot_id', 'booking_id.hour_offset', 'appointment_type_id')
    def _compute_appointment_time(self):
        """Compute appointment time from the selected time slot based on duration"""
        for record in self:
            if record.booking_id and record.booking_id.slot_id:
                # Get the slot and hour_offset from booking (booking.slot_id is the source of truth)
                slot = record.booking_id.slot_id
                hour_offset = record.booking_id.hour_offset if hasattr(record.booking_id, 'hour_offset') and record.booking_id.hour_offset is not None else 0
                
                # Get appointment duration from appointment type
                # The field name is 'appointment_duration'
                duration_hours = 1.0  # Default to 1 hour
                if record.appointment_type_id:
                    if hasattr(record.appointment_type_id, 'appointment_duration') and record.appointment_type_id.appointment_duration:
                        duration_hours = float(record.appointment_type_id.appointment_duration)
                    elif hasattr(record.appointment_type_id, 'duration') and record.appointment_type_id.duration:
                        duration_hours = float(record.appointment_type_id.duration)
                elif slot.appointment_type_id:
                    if hasattr(slot.appointment_type_id, 'appointment_duration') and slot.appointment_type_id.appointment_duration:
                        duration_hours = float(slot.appointment_type_id.appointment_duration)
                    elif hasattr(slot.appointment_type_id, 'duration') and slot.appointment_type_id.duration:
                        duration_hours = float(slot.appointment_type_id.duration)
                
                if duration_hours <= 0:
                    duration_hours = 1.0
                
                # Calculate slot start and end times based on duration
                slot_start_hour = slot.start_hour + (hour_offset * duration_hours)
                slot_end_hour = slot_start_hour + duration_hours
                
                # Format time with AM/PM
                start_hour_int = int(slot_start_hour)
                start_minute = int(round((slot_start_hour % 1) * 60))
                
                start_period = 'AM' if start_hour_int < 12 else 'PM'
                start_hour_12 = start_hour_int if start_hour_int <= 12 else start_hour_int - 12
                if start_hour_12 == 0:
                    start_hour_12 = 12
                
                end_hour_int = int(slot_end_hour)
                end_minute = int(round((slot_end_hour % 1) * 60))
                
                end_period = 'AM' if end_hour_int < 12 else 'PM'
                end_hour_12 = end_hour_int if end_hour_int <= 12 else end_hour_int - 12
                if end_hour_12 == 0:
                    end_hour_12 = 12
                
                # Format as "9:00 AM - 10:00 AM" or "9:00 AM - 9:30 AM" based on duration
                record.appointment_time = f"{start_hour_12}:{start_minute:02d} {start_period} - {end_hour_12}:{end_minute:02d} {end_period}"
            elif record.time_slot_id:
                # Fallback: if no booking, use slot's start and end times
                slot = record.time_slot_id
                start_hour_float = slot.start_hour
                end_hour_float = slot.end_hour if slot.end_hour else start_hour_float + 1
                
                start_hour_int = int(start_hour_float)
                end_hour_int = int(end_hour_float)
                
                start_minute = int(round((start_hour_float % 1) * 60))
                end_minute = int(round((end_hour_float % 1) * 60))
                
                # Format with AM/PM
                start_period = 'AM' if start_hour_int < 12 else 'PM'
                start_hour_12 = start_hour_int if start_hour_int <= 12 else start_hour_int - 12
                if start_hour_12 == 0:
                    start_hour_12 = 12
                
                end_period = 'AM' if end_hour_int < 12 else 'PM'
                end_hour_12 = end_hour_int if end_hour_int <= 12 else end_hour_int - 12
                if end_hour_12 == 0:
                    end_hour_12 = 12
                
                record.appointment_time = f"{start_hour_12}:{start_minute:02d} {start_period} - {end_hour_12}:{end_minute:02d} {end_period}"
            else:
                record.appointment_time = False
    
    @api.model
    def get_available_slots(self, date_str, appointment_type_id=None, exclude_appointment_id=None, zip_code=None):
        """Get available time slots for a given date
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            appointment_type_id: ID of the appointment type (optional)
            exclude_appointment_id: ID of appointment to exclude from booked slots check (for editing)
            zip_code: Customer's zip code to check partner availability
            
        Returns:
            List of dicts with slot information: [{'id': int, 'name': str, 'time_range': str}, ...]
        """
        try:
            selected_date = fields.Date.from_string(date_str)
        except:
            return []
        
        # Get appointment type
        if not appointment_type_id:
            appointment_type_id = self._get_default_appointment_type()
        
        if not appointment_type_id:
            return []
        
        appointment_type = self.env['appointment.type'].browse(appointment_type_id)
        if not appointment_type.exists():
            return []
        
        # Get appointment duration in hours (e.g., 0.5 for 30 minutes, 1.0 for 1 hour)
        # The field name is 'appointment_duration' and it's stored as a float in hours
        duration_hours = 1.0  # Default to 1 hour
        
        # Try to get duration from appointment type
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            # Check for 'appointment_duration' field (the actual field name)
            if 'appointment_duration' in appointment_type._fields:
                duration_value = appointment_type.appointment_duration
                _logger.info(f"Raw appointment_duration value from appointment type '{appointment_type.name}': {duration_value} (type: {type(duration_value)})")
                
                if duration_value:
                    # Duration is stored as float in hours (e.g., 0.5 for 30 minutes, 1.0 for 1 hour)
                    # If it's already a float/int, use it directly
                    if isinstance(duration_value, (int, float)):
                        duration_hours = float(duration_value)
                    else:
                        # Try to convert to float
                        try:
                            duration_hours = float(duration_value)
                        except (ValueError, TypeError):
                            _logger.warning(f"Could not convert appointment_duration value '{duration_value}' to float. Using default 1.0 hour.")
                            duration_hours = 1.0
                else:
                    _logger.warning(f"appointment_duration field exists but is empty/False for appointment type '{appointment_type.name}'. Using default 1.0 hour.")
            # Also check for 'duration' field as fallback (in case some Odoo versions use different field names)
            elif 'duration' in appointment_type._fields:
                duration_value = appointment_type.duration
                _logger.info(f"Found 'duration' field (fallback) from appointment type '{appointment_type.name}': {duration_value} (type: {type(duration_value)})")
                
                if duration_value:
                    if isinstance(duration_value, (int, float)):
                        duration_hours = float(duration_value)
                    else:
                        try:
                            duration_hours = float(duration_value)
                        except (ValueError, TypeError):
                            _logger.warning(f"Could not convert duration value '{duration_value}' to float. Using default 1.0 hour.")
                            duration_hours = 1.0
                else:
                    _logger.warning(f"duration field exists but is empty/False for appointment type '{appointment_type.name}'. Using default 1.0 hour.")
            else:
                _logger.warning(f"Neither 'appointment_duration' nor 'duration' field exists in appointment type '{appointment_type.name}'. Available fields: {list(appointment_type._fields.keys())[:10]}. Using default 1.0 hour.")
        except Exception as e:
            # If duration field doesn't exist or can't be accessed, use default
            _logger.warning(f"Error getting appointment_duration from appointment type '{appointment_type.name}': {e}. Using default 1.0 hour.")
        
        # Ensure minimum duration of 0.25 hours (15 minutes)
        if duration_hours <= 0:
            duration_hours = 1.0
        
        # Debug: Log the final duration for troubleshooting
        _logger.info(f"Appointment type '{appointment_type.name}' (ID: {appointment_type.id}) - Final duration: {duration_hours} hours ({duration_hours * 60} minutes)")
        
        # Get day of week (1=Monday, 7=Sunday)
        weekday = str(selected_date.isoweekday())
        
        # Get all slots for this weekday from the appointment type
        available_slots = self.env['appointment.slot'].search([
            ('appointment_type_id', '=', appointment_type_id),
            ('weekday', '=', weekday),
            ('slot_type', '=', 'recurring')
        ], order='start_hour')
        
        # Get partners with matching zip codes if zip_code is provided
        partner_ids = []
        if zip_code:
            PartnerZipCode = self.env['laundry.partner.zip.code'].sudo()
            partner_zip_assignments = PartnerZipCode.search([])
            
            # Collect all partner user IDs who have this zip code assigned
            for assignment in partner_zip_assignments:
                for zip_code_line in assignment.zip_code_line_ids:
                    if zip_code_line.description and zip_code_line.description.strip() == zip_code.strip():
                        if assignment.user_id and assignment.user_id.partner_id:
                            partner_ids.append(assignment.user_id.partner_id.id)
                            break  # Found match for this assignment, move to next
        
        # Get already booked slots for this date
        # Exclude the current appointment's booking if editing
        domain = [
            ('booking_date', '=', selected_date),
            ('status', '=', 'active')
        ]
        if exclude_appointment_id:
            domain.append(('appointment_id', '!=', exclude_appointment_id))
        
        booked_bookings = self.env['laundry.appointment.booking'].search(domain)
        
        # Create a mapping of (slot_id, hour_offset) -> count of active bookings
        # Count ALL active bookings (pending or confirmed) for each slot
        # This helps us check if number of bookings >= number of available partners
        booked_slot_counts = {}
        for booking in booked_bookings:
            slot = booking.slot_id
            if slot:
                hour_offset = booking.hour_offset if hasattr(booking, 'hour_offset') and booking.hour_offset is not None else 0
                key = (slot.id, hour_offset)
                
                # Count all active bookings (pending or confirmed)
                # Cancelled bookings are excluded (status='cancelled' not in domain)
                if key not in booked_slot_counts:
                    booked_slot_counts[key] = 0
                booked_slot_counts[key] += 1
        
        # Format slots for frontend - break down into slots based on duration
        result = []
        for slot in available_slots:
            start_hour = slot.start_hour
            end_hour = slot.end_hour if slot.end_hour else start_hour + 1
            
            # Calculate total time span in hours
            total_hours = end_hour - start_hour
            
            # Calculate number of slots that fit in this time range based on duration
            num_slots = int(total_hours / duration_hours)
            
            # Generate slots based on duration
            for slot_offset in range(num_slots):
                # Calculate the start time for this slot
                slot_start_hour = start_hour + (slot_offset * duration_hours)
                slot_end_hour = slot_start_hour + duration_hours
                
                # Use slot_offset as hour_offset for backward compatibility with booking system
                hour_offset = slot_offset
                key = (slot.id, hour_offset)
                
                # If zip_code is provided, check partner availability
                if zip_code and partner_ids:
                    # Get count of active bookings for this slot
                    booking_count = booked_slot_counts.get(key, 0)
                    num_partners = len(partner_ids)
                    
                    # If number of active bookings >= number of available partners, hide the slot
                    # This means all partners are either booked or have pending requests
                    if booking_count >= num_partners:
                        continue  # All partners are booked/pending, skip this slot
                else:
                    # Fallback to old behavior: if any booking exists, skip the slot
                    if key in booked_slot_counts:
                        continue  # Skip this hour, it's already booked
                
                # Calculate the start and end time for this slot based on duration
                # slot_start_hour and slot_end_hour are already calculated above
                
                # Format time with AM/PM for start
                start_hour_int = int(slot_start_hour)
                start_minute = int(round((slot_start_hour % 1) * 60))
                
                start_period = 'AM' if start_hour_int < 12 else 'PM'
                start_hour_12 = start_hour_int if start_hour_int <= 12 else start_hour_int - 12
                if start_hour_12 == 0:
                    start_hour_12 = 12
                
                # Format time with AM/PM for end
                end_hour_int = int(slot_end_hour)
                end_minute = int(round((slot_end_hour % 1) * 60))
                
                end_period = 'AM' if end_hour_int < 12 else 'PM'
                end_hour_12 = end_hour_int if end_hour_int <= 12 else end_hour_int - 12
                if end_hour_12 == 0:
                    end_hour_12 = 12
                
                time_range = f"{start_hour_12}:{start_minute:02d} {start_period} - {end_hour_12}:{end_minute:02d} {end_period}"
                
                # Create composite ID: "slot_id:hour_offset" to track which hour within the slot
                composite_id = f"{slot.id}:{hour_offset}"
                
                result.append({
                    'id': composite_id,  # Use composite ID for hourly tracking
                    'slot_id': slot.id,  # Keep original slot_id for reference
                    'hour_offset': hour_offset,  # Track which hour within the slot
                    'name': slot.display_name,
                    'time_range': time_range,
                    'weekday': dict(slot._fields['weekday'].selection).get(weekday, '')
                })
        
        return result
    

