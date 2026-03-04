from odoo import http, fields
from odoo.http import request
from odoo.http import Response
from odoo.addons.portal.controllers.portal import CustomerPortal
import json
from datetime import datetime


class CustomerPortalController(CustomerPortal):
    """Extend CustomerPortal to provide zip codes for customer account page"""
    
    def _get_mandatory_address_fields(self, country_sudo):
        """Override to make zip code and phone optional"""
        field_names = super()._get_mandatory_address_fields(country_sudo)
        # Remove zip and phone from required fields
        field_names.discard('zip')
        field_names.discard('phone')
        return field_names
    
    def _get_mandatory_billing_address_fields(self, country_sudo):
        """Override to make phone optional and mobile required for billing address"""
        base_fields = super()._get_mandatory_billing_address_fields(country_sudo)
        # Remove phone from required fields
        base_fields.discard('phone')
        # Add mobile to required fields
        base_fields.add('mobile')
        return base_fields
    
    def _get_mandatory_delivery_address_fields(self, country_sudo):
        """Override to make phone optional and mobile required for delivery address"""
        base_fields = super()._get_mandatory_delivery_address_fields(country_sudo)
        # Remove phone from required fields
        base_fields.discard('phone')
        # Add mobile to required fields
        base_fields.add('mobile')
        return base_fields
    
    @http.route(
        '/my/address/submit',
        type='http',
        methods=['POST'],
        auth='user',
        website=True,
        sitemap=False,
        csrf=True
    )
    def portal_address_submit(self, partner_id=None, **form_data):
        """Override to ensure proper JSON response with correct content-type and handle availability_weekdays"""
        # Handle checkbox availability_weekdays field
        # HTML checkboxes with same name send values as a list, convert to comma-separated string
        # Always check request.httprequest.form first to get all checkbox values
        import logging
        _logger = logging.getLogger(__name__)
        
        availability = None
        
        # First check request.httprequest.form (direct form submission) - this gets ALL checkbox values
        if hasattr(request.httprequest, 'form'):
            # Use getlist to get all values for checkboxes with same name
            form_values = request.httprequest.form.getlist('availability_weekdays')
            _logger.info(f"Form values from getlist: {form_values}")
            if form_values:
                availability = form_values
        
        # Also check request.params (Odoo's processed params)
        if not availability and hasattr(request, 'params'):
            params_values = request.params.getlist('availability_weekdays') if hasattr(request.params, 'getlist') else None
            if not params_values and 'availability_weekdays' in request.params:
                params_values = request.params.get('availability_weekdays')
            if params_values:
                if isinstance(params_values, list):
                    availability = params_values
                else:
                    availability = [params_values]
            _logger.info(f"Params values: {params_values}")
        
        # Fallback to form_data if not found in form
        if not availability and 'availability_weekdays' in form_data:
            availability = form_data.get('availability_weekdays')
            _logger.info(f"Form data availability: {availability}, type: {type(availability)}")
            # If it's a string, try to split it (might be comma-separated already)
            if isinstance(availability, str) and availability:
                availability = [v.strip() for v in availability.split(',') if v.strip()]
        
        # Process availability values
        if availability:
            if isinstance(availability, list):
                # Filter out empty strings and join with comma
                availability_str = ','.join([str(v).strip() for v in availability if v and str(v).strip()])
                _logger.info(f"Processed availability list to string: {availability_str}")
            else:
                # Single value, convert to string
                availability_str = str(availability).strip() if availability else ''
                _logger.info(f"Processed availability single value to string: {availability_str}")
            
            form_data['availability_weekdays'] = availability_str
        else:
            form_data['availability_weekdays'] = ''
            _logger.info("No availability values found, setting to empty string")
        
        _logger.info(f"Final form_data['availability_weekdays']: {form_data.get('availability_weekdays')}")
        
        # Call parent method to get the JSON string
        json_string = super().portal_address_submit(partner_id=partner_id, **form_data)
        # Return with proper content-type header so JavaScript can parse it
        # Use Response object directly to ensure proper headers
        response = Response(
            json_string,
            content_type='application/json;charset=utf-8'
        )
        return response
    
    def _prepare_address_form_values(self, partner_sudo=None, **kwargs):
        """Override to add zip codes from laundry.zip.code.line for customers"""
        values = super(CustomerPortalController, self)._prepare_address_form_values(
            partner_sudo=partner_sudo, **kwargs
        )
        
        # Only add zip codes if user is in customer group
        if request.env.user.has_group('custom_laundry_service.group_customer'):
            # Get all zip codes from laundry.zip.code.line
            ZipCodeLine = request.env['laundry.zip.code.line'].sudo()
            zip_code_lines = ZipCodeLine.search([])
            zip_codes = [
                {'id': zc.id, 'code': zc.description}
                for zc in zip_code_lines
                if zc.description
            ]
            values['available_zip_codes'] = zip_codes
        
        return values


class CustomerController(http.Controller):

    @http.route(['/my/appointments', '/my/appointments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_appointments(self, page=1, **kw):
        """Appointments list page - default view"""
        values = {
            'page_name': 'my_appointments',
        }
        
        # Get appointments for current user's partner
        # Use sudo() to read product relationships
        Appointment = request.env['laundry.appointment'].sudo()
        partner_id = request.env.user.partner_id.id
        
        # Search appointments for current user
        appointments = Appointment.search([
            ('partner_id', '=', partner_id)
        ])
        
        # Format appointments for template
        appointment_list = []
        status_colors = {
            'pending': 'warning',
            'confirmed': 'info',
            'in_progress': 'primary',
            'pickup': 'info',
            'delivery': 'primary',
            'completed': 'success',
            'cancelled': 'danger'
        }
        
        for apt in appointments:
            # Get service type names as comma-separated string
            # Handle case where relation table might not exist yet
            try:
                service_types = ', '.join(apt.service_type_ids.mapped('name')) if apt.service_type_ids else ''
            except Exception:
                service_types = ''
            
            # Get completion images if status is 'completed' or 'delivery'
            completion_images = []
            if apt.status in ['completed', 'delivery']:
                attachments = request.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'laundry.appointment'),
                    ('res_id', '=', apt.id),
                    ('res_field', '=', 'completion_images')
                ])
                for att in attachments:
                    # Use custom route to serve images with proper authentication
                    image_url = f'/my/service-requests/image/{att.id}'
                    completion_images.append({
                        'id': att.id,
                        'name': att.name,
                        'url': image_url,
                        'type': att.mimetype or 'image/jpeg'
                    })
            
            # Build full customer name from partner fields if available
            customer_name = apt.customer_name  # Default fallback
            if apt.partner_id:
                name_parts = []
                if apt.partner_id.name:
                    name_parts.append(apt.partner_id.name)
                if apt.partner_id.middle_name:
                    name_parts.append(apt.partner_id.middle_name)
                if apt.partner_id.last_name:
                    name_parts.append(apt.partner_id.last_name)
                
                if name_parts:
                    customer_name = ' '.join(name_parts)
            
            appointment_list.append({
                'id': apt.id,
                'date_time': apt.date_time_display or f"{apt.appointment_date} {apt.appointment_time}",
                'service_type': service_types,
                'customer_name': customer_name,
                'phone': apt.phone,
                'status': apt.status.title().replace('_', ' '),
                'status_value': apt.status,  # Raw status value for conditional logic
                'status_color': status_colors.get(apt.status, 'secondary'),
                'completion_images': completion_images
            })
        
        values.update({
            'appointments': appointment_list,
            'json': json  # Allow json.dumps in template
        })
        
        return request.render('custom_laundry_service.portal_my_appointments', values)

    @http.route('/my/appointments/book', type='http', auth="public", website=True, methods=['GET', 'POST'], csrf=True)
    @http.route('/my/appointments/book', type='http', auth="public", website=True, methods=['GET', 'POST'])
    def portal_book_appointment(self, **kw):
        """Book Appointment form page - create/edit"""
        # Get product_id from query parameter (if coming from pricing page)
        product_id = kw.get('product_id') or request.httprequest.args.get('product_id')
        
        # Check if user is logged in
        if request.env.user._is_public():
            # If not logged in, redirect to signup page with redirect_to_booking flag
            redirect_url = '/web/signup?signup_type=customer&redirect_to_booking=1'
            if product_id:
                redirect_url += f'&product_id={product_id}'
            return request.redirect(redirect_url)
        
        # Check if user is in customer group
        if not request.env.user.has_group('custom_laundry_service.group_customer'):
            # Redirect to signup page for non-customers with redirect_to_booking flag
            redirect_url = '/web/signup?signup_type=customer&redirect_to_booking=1'
            if product_id:
                redirect_url += f'&product_id={product_id}'
            return request.redirect(redirect_url)
        
        values = {
            'page_name': 'book_appointment',
        }
        
        # Get product_id from query parameter (if coming from pricing page)
        # Note: pricing page uses product.template IDs, but we need product.product IDs
        product_id = kw.get('product_id') or request.httprequest.args.get('product_id')
        preselected_product_id = None
        if product_id:
            try:
                template_id = int(product_id)
                # Convert product.template ID to product.product ID
                ProductTemplate = request.env['product.template'].sudo()
                template = ProductTemplate.browse(template_id)
                if template.exists():
                    # Get the product.product variant (usually there's one variant per template)
                    product_variant = template.product_variant_id
                    if product_variant:
                        preselected_product_id = product_variant.id
            except (ValueError, TypeError):
                preselected_product_id = None
        
        values['preselected_product_id'] = preselected_product_id
        
        # Service products will be loaded via JavaScript API
        # Get all ironing products organized by service size
        Product = request.env['product.product'].sudo()
        ironing_products_all = Product.search([
            ('type', '=', 'service'),
            ('sale_ok', '=', True),
            ('service_size', 'in', ['small_ironing', 'medium_ironing', 'large_ironing'])
        ])
        
        # Organize ironing products by service_size
        ironing_products_dict = {}
        for ironing_product in ironing_products_all:
            service_size = ironing_product.product_tmpl_id.service_size if ironing_product.product_tmpl_id else None
            if service_size:
                ironing_products_dict[service_size] = {
                    'id': ironing_product.id,
                    'name': ironing_product.name,
                    'service_size': service_size,
                }
        
        # For backward compatibility, also set a single ironing_product (first one found)
        ironing_product = None
        if ironing_products_dict:
            # Get first available ironing product
            first_key = list(ironing_products_dict.keys())[0]
            ironing_product = ironing_products_dict[first_key]
        
        values['ironing_product'] = ironing_product
        values['ironing_products'] = ironing_products_dict  # All ironing products organized by size
        
        # Handle form submission
        if request.httprequest.method == 'POST':
            # Get form data
            customer_name = kw.get('customer_name')
            email = kw.get('email')
            phone = kw.get('phone')
            zip_code = kw.get('zip_code')
            
            # Handle multi-select: HTML forms send multiple values
            # Get form data - try multiple methods to get all selected values
            appointment_date = kw.get('appointment_date')
            time_slot_id_raw = kw.get('time_slot_id')  # May be composite ID "slot_id:hour_offset"
            notes = kw.get('notes')
            pickup_address = kw.get('pickup_address', '').strip()
            delivery_address = kw.get('delivery_address', '').strip()
            pickup_city = kw.get('pickup_city', '').strip()
            pickup_state_id = kw.get('pickup_state_id')
            pickup_country_id = kw.get('pickup_country_id')
            appointment_id = kw.get('id')
            
            # Parse composite ID if it's in format "slot_id:hour_offset"
            time_slot_id = None
            hour_offset = 0
            if time_slot_id_raw:
                if ':' in str(time_slot_id_raw):
                    # Composite ID format: "slot_id:hour_offset"
                    slot_id_str, hour_offset_str = str(time_slot_id_raw).split(':', 1)
                    try:
                        time_slot_id = int(slot_id_str)
                        hour_offset = int(hour_offset_str)
                    except (ValueError, TypeError):
                        time_slot_id = None
                        hour_offset = 0
                else:
                    # Legacy format: just slot_id (for backward compatibility)
                    try:
                        time_slot_id = int(time_slot_id_raw)
                        hour_offset = 0
                    except (ValueError, TypeError):
                        time_slot_id = None
                        hour_offset = 0
            
            # Get service_type_ids from form - handle single value
            service_type_id_raw = None
            if hasattr(request.httprequest, 'form'):
                service_type_id_raw = request.httprequest.form.get('service_type_ids')
            
            # Method 2: Check kw dictionary (Odoo's processed params)
            if not service_type_id_raw:
                service_type_id_raw = kw.get('service_type_ids') or kw.get('service_type_id')
            
            # Parse service type ID (single value)
            service_type_ids = []
            if service_type_id_raw:
                if isinstance(service_type_id_raw, list):
                    # If it's a list, take the first value
                    if service_type_id_raw and len(service_type_id_raw) > 0:
                        try:
                            service_type_ids = [int(service_type_id_raw[0])]
                        except (ValueError, TypeError):
                            service_type_ids = []
                elif isinstance(service_type_id_raw, str):
                    # Single value string
                    try:
                        if service_type_id_raw.strip():
                            service_type_ids = [int(service_type_id_raw.strip())]
                    except (ValueError, AttributeError):
                        service_type_ids = []
                else:
                    # Try to convert to int
                    try:
                        service_type_ids = [int(service_type_id_raw)]
                    except (ValueError, TypeError):
                        service_type_ids = []
            
            # Get ironing product ID if checkbox is checked
            ironing_product_id_raw = kw.get('ironing_product_id') or (hasattr(request.httprequest, 'form') and request.httprequest.form.get('ironing_product_id'))
            if ironing_product_id_raw:
                try:
                    ironing_product_id = int(ironing_product_id_raw)
                    # Add ironing product to service_type_ids if checked
                    if ironing_product_id and ironing_product_id not in service_type_ids:
                        service_type_ids.append(ironing_product_id)
                except (ValueError, TypeError):
                    pass
            
            # Debug: Check what we received
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"Form submission - service_type_id_raw type: {type(service_type_id_raw)}, value: {service_type_id_raw}")
            _logger.info(f"Parsed service_type_ids: {service_type_ids}")
            _logger.info(f"All form data keys: {list(kw.keys())}")
            if hasattr(request.httprequest, 'form'):
                _logger.info(f"Form keys: {list(request.httprequest.form.keys())}")
            
            # Validate: at least one service type must be selected
            if not service_type_ids:
                # Re-render form with error
                appointment = {
                    'customer_name': customer_name or '',
                    'email': email or '',
                    'phone': phone or '',
                    'zip_code': zip_code or '',
                    'service_type_ids': [],
                    'appointment_date': appointment_date or '',
                    'notes': notes or '',
                    'pickup_address': pickup_address or '',
                    'delivery_address': delivery_address or ''
                }
                values.update({
                    'appointment': appointment,
                    'appointment_id': appointment_id,
                    'error': 'Please select at least one service type.'
                })
                return request.render('custom_laundry_service.portal_book_appointment', values)
            
            # Save to model
            # Use sudo() to bypass access restrictions for product.product
            # We validate ownership before updating
            Appointment = request.env['laundry.appointment'].sudo()
            partner_id = request.env.user.partner_id.id
            
            appointment_vals = {
                'customer_name': customer_name,
                'email': email or False,
                'phone': phone,
                'zip_code': zip_code or False,
                'appointment_date': appointment_date,
                'time_slot_id': int(time_slot_id) if time_slot_id else False,  # Changed from appointment_time
                'notes': notes or False,
                'pickup_address': pickup_address or False,
                'delivery_address': delivery_address or False,
                'pickup_city': pickup_city or False,
                'pickup_state_id': int(pickup_state_id) if pickup_state_id else False,
                'pickup_country_id': int(pickup_country_id) if pickup_country_id else False,
                'partner_id': partner_id,
                'service_type_ids': [(6, 0, service_type_ids)] if service_type_ids else [(5, 0, 0)],  # Many2many: replace all (or clear if empty)
            }
            
            try:
                if appointment_id:
                    # Update existing appointment
                    appointment = Appointment.browse(int(appointment_id))
                    # Check if user owns this appointment
                    if appointment.partner_id.id == partner_id:
                        # Get old booking details for comparison
                        old_booking = appointment.booking_id
                        old_slot_id = old_booking.slot_id.id if old_booking and old_booking.slot_id else None
                        old_hour_offset = old_booking.hour_offset if old_booking and hasattr(old_booking, 'hour_offset') else 0
                        old_booking_date = old_booking.booking_date if old_booking else None
                        
                        # Convert new date to date object for comparison
                        new_booking_date = None
                        if appointment_date:
                            try:
                                new_booking_date = fields.Date.from_string(appointment_date)
                            except:
                                new_booking_date = None
                        
                        # Check if slot, hour_offset, or date changed
                        slot_changed = (old_slot_id is None) or (old_slot_id != int(time_slot_id or 0))
                        hour_offset_changed = (old_hour_offset != hour_offset)
                        # Compare dates - both should be date objects or both None
                        date_changed = (old_booking_date != new_booking_date)
                        
                        # Release old booking if any booking detail changed
                        # IMPORTANT: Cancel BEFORE writing appointment so constraint doesn't see it
                        booking_was_cancelled = False
                        if old_booking and (slot_changed or hour_offset_changed or date_changed):
                            # Cancel the old booking first
                            old_booking.write({'status': 'cancelled'})
                            # Clear the booking_id reference on appointment
                            appointment.booking_id = False
                            booking_was_cancelled = True
                            old_booking = None  # Clear reference
                        
                        appointment.write(appointment_vals)
                        
                        # Save pickup address fields to user's partner record if provided
                        if pickup_address or pickup_city or pickup_state_id or pickup_country_id:
                            current_partner = request.env.user.partner_id
                            partner_vals = {}
                            if pickup_address:
                                partner_vals['street'] = pickup_address
                            if pickup_city:
                                partner_vals['city'] = pickup_city
                            if pickup_state_id:
                                partner_vals['state_id'] = int(pickup_state_id)
                            if pickup_country_id:
                                partner_vals['country_id'] = int(pickup_country_id)
                            if partner_vals:
                                current_partner.sudo().write(partner_vals)
                        
                        # Create new booking for the slot if we have slot and date
                        # Only create if we cancelled the old one or if there was no booking
                        if time_slot_id and appointment_date:
                            # Check if we need to create a new booking
                            needs_new_booking = False
                            if booking_was_cancelled:
                                # Old booking was cancelled, need to create new one
                                needs_new_booking = True
                            elif not appointment.booking_id:
                                # No existing booking, need to create one
                                needs_new_booking = True
                            
                            if needs_new_booking:
                                booking_vals = {
                                    'appointment_id': appointment.id,
                                    'slot_id': int(time_slot_id),
                                    'hour_offset': hour_offset,
                                    'booking_date': appointment_date,
                                    'status': 'active'
                                }
                            booking = request.env['laundry.appointment.booking'].sudo().create(booking_vals)
                            appointment.write({'booking_id': booking.id})
                            # Trigger recomputation of appointment_time
                            appointment._compute_appointment_time()
                    else:
                        # User doesn't own this appointment
                        return request.redirect('/my/appointments')
                else:
                    # Create new appointment
                    new_appointment = Appointment.create(appointment_vals)
                    
                    # Create booking for the slot
                    if time_slot_id and appointment_date:
                        booking_vals = {
                            'appointment_id': new_appointment.id,
                            'slot_id': int(time_slot_id),
                            'hour_offset': hour_offset,
                            'booking_date': appointment_date,
                            'status': 'active'
                        }
                        booking = request.env['laundry.appointment.booking'].sudo().create(booking_vals)
                        new_appointment.write({'booking_id': booking.id})
                        # Trigger recomputation of appointment_time
                        new_appointment._compute_appointment_time()
                
                # Save pickup address fields to user's partner record if provided
                if pickup_address or pickup_city or pickup_state_id or pickup_country_id:
                    current_partner = request.env.user.partner_id
                    partner_vals = {}
                    if pickup_address:
                        partner_vals['street'] = pickup_address
                    if pickup_city:
                        partner_vals['city'] = pickup_city
                    if pickup_state_id:
                        partner_vals['state_id'] = int(pickup_state_id)
                    if pickup_country_id:
                        partner_vals['country_id'] = int(pickup_country_id)
                    if partner_vals:
                        current_partner.sudo().write(partner_vals)
                
                return request.redirect('/my/appointments')
            except Exception as e:
                # Handle case where relation table doesn't exist yet
                error_msg = str(e)
                if 'laundry_appointment_product_product_rel' in error_msg or 'does not exist' in error_msg:
                    values.update({
                        'appointment': appointment if 'appointment' in locals() else {
                            'customer_name': customer_name or '',
                            'email': email or '',
                            'phone': phone or '',
                            'zip_code': zip_code or '',
                            'service_type_ids': service_type_ids,
                            'appointment_date': appointment_date or '',
                            'notes': notes or '',
                            'pickup_address': pickup_address or '',
                            'delivery_address': delivery_address or ''
                        },
                        'appointment_id': appointment_id,
                        'error': 'Database table not created. Please upgrade the module: Apps → custom_laundry_service → Upgrade'
                    })
                    return request.render('custom_laundry_service.portal_book_appointment', values)
                else:
                    # Re-raise other errors
                    raise
        
        # Get appointment ID if editing
        appointment_id = kw.get('id')
        appointment = None
        if appointment_id:
            # Load appointment data for editing
            # Use sudo() to read product relationship
            Appointment = request.env['laundry.appointment'].sudo()
            partner_id = request.env.user.partner_id.id
            apt = Appointment.browse(int(appointment_id))
            
            # Check if user owns this appointment
            if apt.partner_id.id == partner_id:
                # Get selected service type IDs as array
                service_type_ids_all = apt.service_type_ids.ids if apt.service_type_ids else []
                
                # Filter out ironing products and get ironing product ID
                Product = request.env['product.product'].sudo()
                service_type_ids = []
                ironing_product_id = None
                for product_id in service_type_ids_all:
                    product = Product.browse(product_id)
                    if product.service_size in ['small_ironing', 'medium_ironing', 'large_ironing']:
                        ironing_product_id = product_id
                    else:
                        service_type_ids.append(product_id)
                # Take first non-ironing product
                service_type_ids = service_type_ids[0:1] if service_type_ids else []
                
                # Get hour_offset from booking if available
                hour_offset = 0
                if apt.booking_id and hasattr(apt.booking_id, 'hour_offset'):
                    hour_offset = apt.booking_id.hour_offset or 0
                
                # Create composite ID for time_slot_id if slot exists
                time_slot_id_value = ''
                if apt.time_slot_id:
                    if hour_offset > 0:
                        time_slot_id_value = f"{apt.time_slot_id.id}:{hour_offset}"
                    else:
                        time_slot_id_value = str(apt.time_slot_id.id)
                
                appointment = {
                    'customer_name': apt.customer_name,
                    'email': apt.email or '',
                    'phone': apt.phone,
                    'zip_code': apt.zip_code or '',
                    'service_type_ids': service_type_ids,
                    'ironing_product_id': ironing_product_id,
                    'appointment_date': apt.appointment_date.strftime('%Y-%m-%d') if apt.appointment_date else '',
                    'time_slot_id': time_slot_id_value,
                    'notes': apt.notes or '',
                    'pickup_address': apt.pickup_address or '',
                    'delivery_address': apt.delivery_address or '',
                    'pickup_city': apt.pickup_city or '',
                    'pickup_state_id': apt.pickup_state_id.id if apt.pickup_state_id else False,
                    'pickup_country_id': apt.pickup_country_id.id if apt.pickup_country_id else False
                }
            else:
                # User doesn't own this appointment, redirect
                return request.redirect('/my/appointments')
        
        # Get all zip codes from backend
        ZipCodeLine = request.env['laundry.zip.code.line'].sudo()
        zip_codes = ZipCodeLine.search([])
        zip_code_list = [{'id': zc.id, 'code': zc.description} for zc in zip_codes if zc.description]
        
        # Get all countries for dropdown
        Country = request.env['res.country'].sudo()
        countries = Country.search([])
        countries_list = [{'id': c.id, 'name': c.name} for c in countries]
        
        # Get customer's account information for auto-population (only for new appointments)
        customer_data = {}
        partner = request.env.user.partner_id
        if not appointment_id:
            customer_data = {
                'customer_name': partner.name or '',
                'email': partner.email or '',
                'phone': partner.phone or '',
                'mobile': partner.mobile or '',
                'zip_code': partner.zip or '',
                'street': partner.street or '',
                'city': partner.city or '',
                'state_id': partner.state_id.id if partner.state_id else False,
                'country_id': partner.country_id.id if partner.country_id else False,
            }
        else:
            # For existing appointments, also include address fields for pickup address auto-population
            customer_data = {}
            if 'street' not in customer_data:
                customer_data['street'] = partner.street or ''
            if 'city' not in customer_data:
                customer_data['city'] = partner.city or ''
            if 'state_id' not in customer_data:
                customer_data['state_id'] = partner.state_id.id if partner.state_id else False
            if 'country_id' not in customer_data:
                customer_data['country_id'] = partner.country_id.id if partner.country_id else False
        
        # Get states for the selected country (if editing appointment or customer has country)
        states_list = []
        selected_country_id = False
        if appointment and appointment.get('pickup_country_id'):
            selected_country_id = appointment.get('pickup_country_id')
        elif customer_data and customer_data.get('country_id'):
            selected_country_id = customer_data.get('country_id')
        
        if selected_country_id:
            State = request.env['res.country.state'].sudo()
            states = State.search([('country_id', '=', selected_country_id)])
            states_list = [{'id': s.id, 'name': s.name} for s in states]
        
        values.update({
            'appointment': appointment,
            'appointment_id': appointment_id,
            'zip_codes': zip_code_list,
            'customer_data': customer_data,
            'countries': countries_list,
            'states': states_list,
            'selected_country_id': selected_country_id,
        })
        
        return request.render('custom_laundry_service.portal_book_appointment', values)

    @http.route('/my/appointments/get_service_products', type='json', auth="user", website=True, methods=['POST'], csrf=True)
    def get_service_products(self, **kw):
        """API endpoint to get service products using JSON-RPC"""
        # Use sudo() to bypass access rights for reading products
        # We only read service products that are sale_ok=True (public products)
        Product = request.env['product.product'].sudo()
        service_products = Product.search([
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ])
        
        products_list = []
        for product in service_products:
            # Get service_size from product template
            service_size = product.product_tmpl_id.service_size if product.product_tmpl_id else False
            products_list.append({
                'id': product.id,
                'name': product.name,
                'service_size': service_size or False,  # Include service_size in response
            })
        
        return products_list

    @http.route('/my/appointments/get_available_slots', type='json', auth="user", website=True, methods=['POST'], csrf=True)
    def get_available_slots(self, **kw):
        """API endpoint to get available time slots for a selected date"""
        date_str = kw.get('date')
        appointment_id = kw.get('appointment_id')
        zip_code = kw.get('zip_code')
        
        if not date_str:
            return {'error': 'Date is required'}
        
        # Convert appointment_id to int if provided, otherwise None
        exclude_appointment_id = None
        if appointment_id:
            try:
                exclude_appointment_id = int(appointment_id)
            except (ValueError, TypeError):
                exclude_appointment_id = None
        
        # Get zip code from customer's account if not provided
        if not zip_code:
            partner = request.env.user.partner_id
            zip_code = partner.zip
        
        # Use sudo() to access appointment.type and appointment.slot models
        Appointment = request.env['laundry.appointment'].sudo()
        slots = Appointment.get_available_slots(
            date_str, 
            exclude_appointment_id=exclude_appointment_id,
            zip_code=zip_code
        )
        
        return {'slots': slots}

    @http.route('/my/appointments/get_states', type='json', auth="user", website=True, methods=['POST'], csrf=True)
    def get_states(self, **kw):
        """API endpoint to get states for a selected country"""
        country_id = kw.get('country_id')
        
        if not country_id:
            return {'states': []}
        
        try:
            country_id = int(country_id)
        except (ValueError, TypeError):
            return {'states': []}
        
        # Get states for the selected country
        State = request.env['res.country.state'].sudo()
        states = State.search([('country_id', '=', country_id)])
        
        states_list = [{'id': s.id, 'name': s.name} for s in states]
        
        return {'states': states_list}

    @http.route('/my/appointments/cancel', type='json', auth="user", website=True, methods=['POST'], csrf=True)
    def cancel_appointment(self, **kw):
        """Cancel an appointment via JSON-RPC"""
        appointment_id = kw.get('appointment_id')
        
        if not appointment_id:
            raise ValueError('Missing appointment_id')
        
        Appointment = request.env['laundry.appointment'].sudo()
        appointment = Appointment.browse(int(appointment_id))
        
        if not appointment.exists():
            raise ValueError('Appointment not found')
        
        # Get current partner
        current_partner = request.env.user.partner_id
        
        # Validation: Only the owner can cancel
        if appointment.partner_id.id != current_partner.id:
            raise ValueError('You can only cancel your own appointments')
        
        # Validation: Can only cancel pending appointments
        if appointment.status != 'pending':
            raise ValueError('Only pending appointments can be cancelled')
        
        # Release the booking if it exists
        if appointment.booking_id:
            appointment.booking_id.write({'status': 'cancelled'})
        
        # Update status to cancelled
        appointment.write({'status': 'cancelled'})
        
        return {'success': True, 'message': 'Appointment cancelled successfully'}

