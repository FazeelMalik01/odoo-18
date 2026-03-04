from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import logging
import json
import base64

_logger = logging.getLogger(__name__)


class PartnerController(CustomerPortal):
    
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

    @http.route('/my/service-requests', type='http', auth="user", website=True)
    def portal_my_service_requests(self, **kw):
        """Service Requests list page for portal users"""
        values = {
            'page_name': 'my_service_requests',
        }
        
        # Get current partner
        current_partner = request.env.user.partner_id
        
        # Get all zip codes assigned to this partner
        PartnerZipCode = request.env['laundry.partner.zip.code'].sudo()
        partner_zip_assignments = PartnerZipCode.search([
            ('user_id', '=', request.env.user.id)
        ])
        
        # Collect all unique zip codes assigned to this partner
        partner_zip_codes = set()
        for assignment in partner_zip_assignments:
            for zip_code_line in assignment.zip_code_line_ids:
                if zip_code_line.description:
                    partner_zip_codes.add(zip_code_line.description.strip())
        
        # Get service requests matching partner's zip codes
        Appointment = request.env['laundry.appointment'].sudo()
        
        # Filter appointments by matching zip code with special logic:
        # - Pending requests: show to all partners with matching zip code, BUT exclude if partner is already booked for that slot
        # - Confirmed/other status: show only to assigned partner
        if partner_zip_codes:
            # Get all appointments where zip_code matches any of partner's assigned zip codes
            all_appointments = Appointment.search([])
            
            # Get all bookings for current partner to check slot availability
            Booking = request.env['laundry.appointment.booking'].sudo()
            partner_bookings = Booking.search([
                ('appointment_id.assigned_partner_id', '=', current_partner.id),
                ('status', '=', 'active')
            ])
            
            # Create a set of (slot_id, hour_offset, booking_date) tuples for partner's bookings
            partner_booked_slots = set()
            for booking in partner_bookings:
                if booking.slot_id and booking.booking_date:
                    hour_offset = booking.hour_offset if hasattr(booking, 'hour_offset') and booking.hour_offset is not None else 0
                    partner_booked_slots.add((booking.slot_id.id, hour_offset, booking.booking_date))
            
            # Get all cancelled bookings to check if slots are free
            cancelled_bookings = Booking.search([
                ('status', '=', 'cancelled')
            ])
            cancelled_slots = set()
            for booking in cancelled_bookings:
                if booking.slot_id and booking.booking_date:
                    hour_offset = booking.hour_offset if hasattr(booking, 'hour_offset') and booking.hour_offset is not None else 0
                    cancelled_slots.add((booking.slot_id.id, hour_offset, booking.booking_date))
            
            # Get user responses to check if current user has rejected any requests
            UserResponse = request.env['laundry.appointment.user.response'].sudo()
            current_user_id = request.env.user.id
            rejected_appointment_ids = set()
            user_responses = UserResponse.search([
                ('user_id', '=', current_user_id),
                ('status', '=', 'rejected')
            ])
            for response in user_responses:
                if response.appointment_id:
                    rejected_appointment_ids.add(response.appointment_id.id)
            
            # Get partner's availability weekdays
            partner_availability = current_partner.availability_weekdays or ''
            partner_availability_list = [day.strip().lower() for day in partner_availability.split(',') if day.strip()]
            
            # Filter logic:
            # 1. Pending requests: Show to ALL partners with matching zip code (if not already booked for that slot)
            # 2. Don't show requests that current user has rejected
            # 3. Confirmed/other status: Show ONLY to assigned partner
            # 4. Cancelled: Show to assigned partner OR to other partners if booking is cancelled (slot is free)
            # 5. Check partner availability: Only show if appointment date matches partner's available days
            def should_show_appointment(a):
                # Must have matching zip code
                if not (a.zip_code and a.zip_code.strip() in partner_zip_codes):
                    return False
                
                # Don't show if current user has rejected this request
                if a.id in rejected_appointment_ids:
                    return False
                
                # Check partner availability: Only show if appointment date matches partner's available days
                # Skip this check if:
                # 1. Already assigned to this partner (show regardless of availability)
                # 2. Partner has no availability set (show all for backward compatibility)
                if not (a.assigned_partner_id and a.assigned_partner_id.id == current_partner.id):
                    # Only check availability if partner has set availability days
                    if partner_availability_list and a.appointment_date:
                        # Get the day of the week for the appointment date
                        # Python's weekday(): Monday=0, Tuesday=1, ..., Sunday=6
                        weekday_map = {
                            0: 'monday',
                            1: 'tuesday',
                            2: 'wednesday',
                            3: 'thursday',
                            4: 'friday',
                            5: 'saturday',
                            6: 'sunday'
                        }
                        appointment_weekday = weekday_map.get(a.appointment_date.weekday())
                        
                        # If appointment date doesn't match any of partner's available days, don't show
                        if appointment_weekday and appointment_weekday not in partner_availability_list:
                            return False
                
                # If assigned to current partner, always show (for all statuses including cancelled)
                if a.assigned_partner_id and a.assigned_partner_id.id == current_partner.id:
                    return True
                
                # If status is confirmed, pickup, in_progress, completed, or delivery
                # Only show to assigned partner (which we already checked above)
                # So don't show to other partners
                if a.status in ['confirmed', 'pickup', 'in_progress', 'completed', 'delivery']:
                    return False
                
                # If cancelled, check if the booking is cancelled (slot is free)
                # If so, show it to other partners so they can claim it
                if a.status == 'cancelled':
                    # Check if this appointment has a cancelled booking
                    if a.booking_id and a.appointment_date and a.booking_id.slot_id:
                        hour_offset = a.booking_id.hour_offset if hasattr(a.booking_id, 'hour_offset') and a.booking_id.hour_offset is not None else 0
                        slot_key = (a.booking_id.slot_id.id, hour_offset, a.appointment_date)
                        # Show if the booking is cancelled (slot is free) and partner is not already booked for this slot
                        if slot_key in cancelled_slots and slot_key not in partner_booked_slots:
                            return True
                    # If no booking info or booking not cancelled, don't show to other partners
                    return False
                
                # If pending, show to all partners with matching zip code (if not already booked for this slot)
                # This allows multiple partners to see the same pending request
                if a.status == 'pending':
                    # Check if this appointment has a booking
                    if a.booking_id and a.appointment_date and a.booking_id.slot_id:
                        hour_offset = a.booking_id.hour_offset if hasattr(a.booking_id, 'hour_offset') and a.booking_id.hour_offset is not None else 0
                        slot_key = (a.booking_id.slot_id.id, hour_offset, a.appointment_date)
                        # Only show if partner is NOT already booked for this slot
                        return slot_key not in partner_booked_slots
                    # If no booking info, show it (fallback)
                    return True
                
                # Should not reach here, but return False as fallback
                return False
            
            appointments = all_appointments.filtered(should_show_appointment)
            
            # Sort by date
            appointments = appointments.sorted(
                key=lambda r: (r.appointment_date or '', r.appointment_time or ''), 
                reverse=True
            )
        else:
            # If partner has no zip codes assigned, show no appointments
            appointments = Appointment.browse()
        
        # Count services done by this partner (confirmed, pickup, in_progress, completed, delivery)
        services_done_count = Appointment.search_count([
            ('assigned_partner_id', '=', current_partner.id),
            ('status', 'in', ['confirmed', 'pickup', 'in_progress', 'completed', 'delivery'])
        ])
        
        # Format appointments for template
        service_requests = []
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
            try:
                service_types = ', '.join(apt.service_type_ids.mapped('name')) if apt.service_type_ids else 'N/A'
            except Exception as e:
                _logger.warning(f"Error getting service types for appointment {apt.id}: {e}")
                service_types = 'N/A'
            
            # Get completion images if status is pickup or delivery
            completion_images = []
            if apt.status in ['pickup', 'delivery']:
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
            
            # Check if current user has responded to this appointment
            UserResponse = request.env['laundry.appointment.user.response'].sudo()
            current_user_id = request.env.user.id
            has_responded = False
            user_response = UserResponse.search([
                ('appointment_id', '=', apt.id),
                ('user_id', '=', current_user_id)
            ], limit=1)
            if user_response:
                has_responded = True
            
            # Build full customer name from partner fields if available
            customer_name = apt.customer_name or ''  # Default fallback
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
            
            service_requests.append({
                'id': apt.id,
                'name': apt.name or 'N/A',
                'date': apt.appointment_date.strftime('%B %d, %Y') if apt.appointment_date else '',
                'time': apt.appointment_time or '',
                'status': apt.status.title().replace('_', ' ') if apt.status else 'Pending',
                'status_value': apt.status or 'pending',  # Raw status value for form
                'status_color': status_colors.get(apt.status, 'secondary'),
                'service_types': service_types,
                'customer_name': customer_name,
                'phone': apt.phone or '',
                'email': apt.email or '',
                'notes': apt.notes or '',
                'completion_images': completion_images,
                'has_responded': has_responded,  # Whether current user has responded (accepted or rejected)
            })
        
        # Check if any service request has status 'pickup' or 'delivery' to show images column
        has_pickup_or_delivery = any(
            sr.get('status_value') in ['pickup', 'delivery'] 
            for sr in service_requests
        )
        
        # Count services done by this partner (confirmed, pickup, in_progress, completed, delivery)
        services_done_count = Appointment.search_count([
            ('assigned_partner_id', '=', current_partner.id),
            ('status', 'in', ['confirmed', 'pickup', 'in_progress', 'completed', 'delivery'])
        ])
        
        values.update({
            'service_requests': service_requests,
            'show_completion_images': has_pickup_or_delivery,
            'services_done_count': services_done_count,
            'json': json,  # Make json available in template for json.dumps
        })
        
        return request.render('custom_laundry_service.portal_my_service_requests', values)
    
    @http.route('/my/service-requests/get_details', type='json', auth="user", website=True, methods=['POST'], csrf=True)
    def get_service_request_details(self, **kw):
        """Get full details of a service request"""
        appointment_id = kw.get('appointment_id')
        
        if not appointment_id:
            raise ValueError('Missing appointment_id')
        
        Appointment = request.env['laundry.appointment'].sudo()
        appointment = Appointment.browse(int(appointment_id))
        
        if not appointment.exists():
            raise ValueError('Appointment not found')
        
        # Get current partner
        current_partner = request.env.user.partner_id
        
        # Validate access: must be assigned to current partner or match zip code
        has_access = False
        if appointment.assigned_partner_id and appointment.assigned_partner_id.id == current_partner.id:
            has_access = True
        else:
            # Check if zip code matches
            PartnerZipCode = request.env['laundry.partner.zip.code'].sudo()
            partner_zip_assignments = PartnerZipCode.search([
                ('user_id', '=', request.env.user.id)
            ])
            partner_zip_codes = set()
            for assignment in partner_zip_assignments:
                for zip_code_line in assignment.zip_code_line_ids:
                    if zip_code_line.description:
                        partner_zip_codes.add(zip_code_line.description.strip())
            
            if appointment.zip_code and appointment.zip_code.strip() in partner_zip_codes:
                has_access = True
        
        if not has_access:
            raise ValueError('Access denied')
        
        # Get service type names
        try:
            service_types = ', '.join(appointment.service_type_ids.mapped('name')) if appointment.service_type_ids else 'N/A'
        except Exception:
            service_types = 'N/A'
        
        # Format date and time
        date_str = appointment.appointment_date.strftime('%B %d, %Y') if appointment.appointment_date else 'N/A'
        time_str = appointment.appointment_time or 'N/A'
        
        # Build full customer name from partner fields if available
        customer_name = appointment.customer_name or 'N/A'  # Default fallback
        if appointment.partner_id:
            name_parts = []
            if appointment.partner_id.name:
                name_parts.append(appointment.partner_id.name)
            if appointment.partner_id.middle_name:
                name_parts.append(appointment.partner_id.middle_name)
            if appointment.partner_id.last_name:
                name_parts.append(appointment.partner_id.last_name)
            
            if name_parts:
                customer_name = ' '.join(name_parts)
        
        # Status mapping
        status_display = {
            'pending': 'Pending',
            'confirmed': 'Confirmed',
            'pickup': 'Pickup',
            'in_progress': 'In Progress',
            'completed': 'Completed',
            'delivery': 'Delivery',
            'cancelled': 'Cancelled'
        }
        
        return {
            'id': appointment.id,
            'name': appointment.name or 'N/A',
            'date': date_str,
            'time': time_str,
            'status': status_display.get(appointment.status, appointment.status.title()),
            'status_value': appointment.status,
            'service_types': service_types,
            'customer_name': customer_name,
            'email': appointment.email or 'N/A',
            'phone': appointment.phone or 'N/A',
            'zip_code': appointment.zip_code or 'N/A',
            'pickup_address': appointment.pickup_address or 'N/A',
            'delivery_address': appointment.delivery_address or 'N/A',
            'notes': appointment.notes or 'N/A',
        }
    
    @http.route('/my/service-requests/update_status', type='json', auth="user", website=True, methods=['POST'], csrf=True)
    def update_service_request_status(self, **kw):
        """Update service request status via JSON-RPC"""
        appointment_id = kw.get('appointment_id')
        new_status = kw.get('status')
        
        if not appointment_id or not new_status:
            raise ValueError('Missing appointment_id or status')
        
        # Validate status
        valid_statuses = ['pending', 'confirmed', 'in_progress', 'pickup', 'delivery', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            raise ValueError('Invalid status')
        
        Appointment = request.env['laundry.appointment'].sudo()
        appointment = Appointment.browse(int(appointment_id))
        
        if not appointment.exists():
            raise ValueError('Appointment not found')
        
        # Get current partner
        current_partner = request.env.user.partner_id
        
        # Validation 1: Cannot revert to pending after confirmation
        if new_status == 'pending' and appointment.status != 'pending':
            raise ValueError('Cannot revert status back to Pending after confirmation')
        
        # Validation 2: If already assigned to a partner, only that partner can change status
        if appointment.assigned_partner_id and appointment.assigned_partner_id.id != current_partner.id:
            raise ValueError('This request has been claimed by another partner')
        
        # Store old status to check if changing to confirmed
        old_status = appointment.status
        
        # Update status
        vals_to_write = {'status': new_status}
        
        # When confirming, assign this partner to the request
        # This ensures that once confirmed, only the confirming partner can see it
        if new_status == 'confirmed':
            # If not already assigned, assign to current partner
            if not appointment.assigned_partner_id or appointment.assigned_partner_id.id != current_partner.id:
                vals_to_write['assigned_partner_id'] = current_partner.id
        
        # When cancelling, handle differently based on current status
        if new_status == 'cancelled':
            # Cancel the booking to free up the slot
            if appointment.booking_id:
                appointment.booking_id.write({'status': 'cancelled'})
            
            # Always set status to 'cancelled' so the partner can see their cancelled request
            # Keep assigned_partner_id so the partner can see their cancelled requests
            # The booking is cancelled, so other partners can see it if the slot is free
            # (handled in the filtering logic)
            pass
        
        appointment.write(vals_to_write)
        
        # Automatically create sales order when status changes to confirmed
        if new_status == 'confirmed' and old_status != 'confirmed':
            try:
                # Call the existing method to create sales order
                appointment.action_create_sale_order()
                return {
                    'success': True, 
                    'message': 'Status updated to Confirmed and Sales Order created successfully. This request is now assigned to you.'
                }
            except Exception as e:
                # If sales order creation fails, still update status but notify
                _logger.error(f"Failed to create sales order for appointment {appointment_id}: {str(e)}")
                return {
                    'success': True, 
                    'message': f'Status updated but Sales Order creation failed: {str(e)}'
                }
        
        return {'success': True, 'message': 'Status updated successfully'}
    
    @http.route('/my/service-requests/approve_request', type='json', auth="user", website=True, methods=['POST'], csrf=True)
    def approve_service_request(self, **kw):
        """Approve a service request - Accept action"""
        appointment_id = kw.get('appointment_id')
        
        if not appointment_id:
            raise ValueError('Missing appointment_id')
        
        Appointment = request.env['laundry.appointment'].sudo()
        appointment = Appointment.browse(int(appointment_id))
        
        if not appointment.exists():
            raise ValueError('Appointment not found')
        
        # Get current user and partner
        current_user = request.env.user
        current_partner = current_user.partner_id
        
        # Validate that appointment is pending
        if appointment.status != 'pending':
            raise ValueError('Only pending requests can be approved')
        
        # Check if user has already responded
        UserResponse = request.env['laundry.appointment.user.response'].sudo()
        existing_response = UserResponse.search([
            ('appointment_id', '=', appointment.id),
            ('user_id', '=', current_user.id)
        ], limit=1)
        
        if existing_response:
            raise ValueError('You have already responded to this request')
        
        # Create user response record with "accepted" status
        UserResponse.create({
            'appointment_id': appointment.id,
            'user_id': current_user.id,
            'status': 'accepted'
        })
        
        # Update appointment status to confirmed and assign to current partner
        appointment.write({
            'status': 'confirmed',
            'assigned_partner_id': current_partner.id
        })
        
        # Find all other pending requests for the same time slot and auto-reject them for this partner
        if appointment.booking_id and appointment.booking_id.slot_id and appointment.appointment_date:
            slot_id = appointment.booking_id.slot_id.id
            hour_offset = appointment.booking_id.hour_offset if hasattr(appointment.booking_id, 'hour_offset') and appointment.booking_id.hour_offset is not None else 0
            booking_date = appointment.appointment_date
            
            # Find all other appointments with the same slot, hour_offset, and date
            other_appointments = Appointment.search([
                ('id', '!=', appointment.id),
                ('status', '=', 'pending'),
                ('booking_id.slot_id', '=', slot_id),
                ('booking_id.hour_offset', '=', hour_offset),
                ('appointment_date', '=', booking_date),
                ('zip_code', '=', appointment.zip_code)  # Same zip code
            ])
            
            # Auto-reject these requests for the current partner
            for other_apt in other_appointments:
                # Check if partner hasn't already responded to this request
                existing_response = UserResponse.search([
                    ('appointment_id', '=', other_apt.id),
                    ('user_id', '=', current_user.id)
                ], limit=1)
                
                if not existing_response:
                    # Create rejection response
                    UserResponse.create({
                        'appointment_id': other_apt.id,
                        'user_id': current_user.id,
                        'status': 'rejected'
                    })
                    
                    # Check if all partners have rejected this request (to auto-cancel)
                    if other_apt.zip_code:
                        zip_code = other_apt.zip_code.strip()
                        
                        # Get all partners assigned to this zip code
                        PartnerZipCode = request.env['laundry.partner.zip.code'].sudo()
                        partner_zip_assignments = PartnerZipCode.search([])
                        
                        partner_user_ids = set()
                        for assignment in partner_zip_assignments:
                            for zip_code_line in assignment.zip_code_line_ids:
                                if zip_code_line.description and zip_code_line.description.strip() == zip_code:
                                    if assignment.user_id:
                                        partner_user_ids.add(assignment.user_id.id)
                                    break
                        
                        # Get all rejection responses for this appointment
                        rejection_responses = UserResponse.search([
                            ('appointment_id', '=', other_apt.id),
                            ('status', '=', 'rejected')
                        ])
                        rejected_user_ids = set(rejection_responses.mapped('user_id.id'))
                        
                        # If all partners have rejected, cancel the appointment
                        if partner_user_ids and rejected_user_ids.issuperset(partner_user_ids):
                            if other_apt.booking_id:
                                other_apt.booking_id.write({'status': 'cancelled'})
                            other_apt.write({'status': 'cancelled'})
        
        # Automatically create sales order when status changes to confirmed
        try:
            appointment.action_create_sale_order()
            return {
                'success': True,
                'message': 'Request approved successfully. Status updated to Confirmed and Sales Order created.'
            }
        except Exception as e:
            _logger.error(f"Error creating sales order: {e}")
            return {
                'success': True,
                'message': 'Request approved successfully. Status updated to Confirmed.'
            }
    
    @http.route('/my/service-requests/reject_request', type='json', auth="user", website=True, methods=['POST'], csrf=True)
    def reject_service_request(self, **kw):
        """Reject a service request - Reject action"""
        appointment_id = kw.get('appointment_id')
        
        if not appointment_id:
            raise ValueError('Missing appointment_id')
        
        Appointment = request.env['laundry.appointment'].sudo()
        appointment = Appointment.browse(int(appointment_id))
        
        if not appointment.exists():
            raise ValueError('Appointment not found')
        
        # Get current user
        current_user = request.env.user
        
        # Validate that appointment is pending
        if appointment.status != 'pending':
            raise ValueError('Only pending requests can be rejected')
        
        # Check if user has already responded
        UserResponse = request.env['laundry.appointment.user.response'].sudo()
        existing_response = UserResponse.search([
            ('appointment_id', '=', appointment.id),
            ('user_id', '=', current_user.id)
        ], limit=1)
        
        if existing_response:
            raise ValueError('You have already responded to this request')
        
        # Create user response record with "rejected" status
        UserResponse.create({
            'appointment_id': appointment.id,
            'user_id': current_user.id,
            'status': 'rejected'
        })
        
        # Check if all partners with matching zip code have rejected
        if appointment.zip_code:
            zip_code = appointment.zip_code.strip()
            
            # Get all partners assigned to this zip code
            PartnerZipCode = request.env['laundry.partner.zip.code'].sudo()
            partner_zip_assignments = PartnerZipCode.search([])
            
            partner_user_ids = set()
            for assignment in partner_zip_assignments:
                for zip_code_line in assignment.zip_code_line_ids:
                    if zip_code_line.description and zip_code_line.description.strip() == zip_code:
                        if assignment.user_id:
                            partner_user_ids.add(assignment.user_id.id)
                        break
            
            # Get all rejection responses for this appointment
            rejection_responses = UserResponse.search([
                ('appointment_id', '=', appointment.id),
                ('status', '=', 'rejected')
            ])
            rejected_user_ids = set(rejection_responses.mapped('user_id.id'))
            
            # If all partners have rejected, cancel the appointment
            if partner_user_ids and rejected_user_ids.issuperset(partner_user_ids):
                # Cancel the booking to free up the slot
                if appointment.booking_id:
                    appointment.booking_id.write({'status': 'cancelled'})
                
                # Update appointment status to cancelled
                appointment.write({'status': 'cancelled'})
                
                return {
                    'success': True,
                    'message': 'Request rejected. All partners have rejected this request, so it has been cancelled.'
                }
        
        return {
            'success': True,
            'message': 'Request rejected. It will no longer appear in your list.'
        }
    
    @http.route('/my/service-requests/upload_images', type='http', auth="user", website=True, methods=['POST'], csrf=False)
    def upload_completion_images(self, **kw):
        """Upload completion images for a service request"""
        try:
            _logger.info("Upload images route called")
            _logger.info(f"Request method: {request.httprequest.method}")
            _logger.info(f"Form data keys: {list(request.httprequest.form.keys())}")
            _logger.info(f"Files keys: {list(request.httprequest.files.keys()) if request.httprequest.files else 'None'}")
            
            # Get appointment_id from form data or kw
            appointment_id = kw.get('appointment_id') or request.httprequest.form.get('appointment_id')
            _logger.info(f"Appointment ID: {appointment_id}")
            if not appointment_id:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Missing appointment_id'}), 
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            Appointment = request.env['laundry.appointment'].sudo()
            appointment = Appointment.browse(int(appointment_id))
            
            if not appointment.exists():
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Appointment not found'}), 
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            # Get current partner
            current_partner = request.env.user.partner_id
            
            # Validation: Only assigned partner can upload images
            if appointment.assigned_partner_id and appointment.assigned_partner_id.id != current_partner.id:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'You are not assigned to this request'}), 
                    headers=[('Content-Type', 'application/json')],
                    status=403
                )
            
            # Validation: Only pickup or delivery requests can have images
            if appointment.status not in ['pickup', 'delivery']:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Images can only be uploaded for pickup or delivery requests'}), 
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # Get uploaded files - handle both single and multiple file uploads
            uploaded_files = []
            
            # Access files from request
            files_dict = request.httprequest.files
            
            # Try different key names that might be used
            possible_keys = ['images[]', 'images', 'file', 'files']
            
            for key in possible_keys:
                if key in files_dict:
                    file_list = files_dict.getlist(key) if hasattr(files_dict, 'getlist') else [files_dict.get(key)]
                    uploaded_files.extend([f for f in file_list if f and hasattr(f, 'filename') and f.filename])
                    break
            
            # If still no files, get all files from request
            if not uploaded_files and files_dict:
                for key in files_dict:
                    file_obj = files_dict.get(key)
                    if file_obj and hasattr(file_obj, 'filename') and file_obj.filename:
                        uploaded_files.append(file_obj)
            
            _logger.info(f"Found {len(uploaded_files)} files to upload from keys: {list(files_dict.keys()) if files_dict else 'None'}")
            
            if not uploaded_files or not any(f.filename for f in uploaded_files):
                return request.make_response(
                    json.dumps({'success': False, 'error': 'No files uploaded'}), 
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # Create attachments
            Attachment = request.env['ir.attachment'].sudo()
            uploaded_attachments = []
            
            for file_obj in uploaded_files:
                if file_obj and file_obj.filename:
                    try:
                        # Read file content
                        file_content = file_obj.read()
                        if not file_content:
                            continue
                        
                        # Get file name and content type
                        filename = file_obj.filename
                        content_type = getattr(file_obj, 'content_type', None) or 'image/jpeg'
                        
                        # Create attachment
                        attachment = Attachment.create({
                            'name': filename,
                            'res_model': 'laundry.appointment',
                            'res_id': appointment.id,
                            'res_field': 'completion_images',
                            'type': 'binary',
                            'datas': base64.b64encode(file_content).decode('utf-8'),
                            'mimetype': content_type,
                        })
                        uploaded_attachments.append({
                            'id': attachment.id,
                            'name': attachment.name,
                            'url': f'/my/service-requests/image/{attachment.id}'
                        })
                    except Exception as e:
                        _logger.error(f"Error uploading file {file_obj.filename}: {str(e)}")
                        continue
            
            if not uploaded_attachments:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Failed to upload files. Please check file format and try again.'}), 
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            return request.make_response(
                json.dumps({
                    'success': True, 
                    'message': f'Successfully uploaded {len(uploaded_attachments)} image(s)',
                    'attachments': uploaded_attachments
                }), 
                headers=[('Content-Type', 'application/json')],
                status=200
            )
        except Exception as e:
            _logger.error(f"Error in upload_completion_images: {str(e)}", exc_info=True)
            return request.make_response(
                json.dumps({'success': False, 'error': f'Server error: {str(e)}'}), 
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/my/service-requests/delete_image', type='json', auth="user", website=True, methods=['POST'], csrf=True)
    def delete_completion_image(self, **kw):
        """Delete a completion image"""
        image_id = kw.get('image_id')
        if not image_id:
            return {'success': False, 'error': 'Missing image_id'}
        
        Attachment = request.env['ir.attachment'].sudo()
        attachment = Attachment.browse(int(image_id))
        
        if not attachment.exists():
            return {'success': False, 'error': 'Image not found'}
        
        # Validation: Check if attachment belongs to an appointment
        if attachment.res_model != 'laundry.appointment':
            return {'success': False, 'error': 'Invalid attachment'}
        
        appointment = request.env['laundry.appointment'].sudo().browse(attachment.res_id)
        if not appointment.exists():
            return {'success': False, 'error': 'Appointment not found'}
        
        # Get current partner
        current_partner = request.env.user.partner_id
        
        # Validation: Only assigned partner can delete images
        if appointment.assigned_partner_id and appointment.assigned_partner_id.id != current_partner.id:
            return {'success': False, 'error': 'You are not assigned to this request'}
        
        # Delete attachment
        attachment.unlink()
        
        return {'success': True, 'message': 'Image deleted successfully'}
    
    @http.route('/my/service-requests/image/<int:attachment_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_completion_image(self, attachment_id, **kwargs):
        """Serve completion images with proper authentication"""
        try:
            Attachment = request.env['ir.attachment'].sudo()
            attachment = Attachment.browse(attachment_id)
            
            if not attachment.exists():
                return request.make_response('Image not found', status=404)
            
            # Validation: Check if attachment belongs to an appointment
            if attachment.res_model != 'laundry.appointment':
                return request.make_response('Invalid attachment', status=403)
            
            # Check if user has access (same logic as service requests list)
            appointment = request.env['laundry.appointment'].sudo().browse(attachment.res_id)
            if not appointment.exists():
                return request.make_response('Appointment not found', status=404)
            
            # Get current partner and user
            current_partner = request.env.user.partner_id
            current_user = request.env.user
            
            # Check access: user can view images if:
            # 1. User is the customer (appointment.partner_id matches current partner), OR
            # 2. Appointment is assigned to current partner (for partners), OR
            # 3. Appointment's zip code matches any of partner's assigned zip codes (for partners)
            
            has_access = False
            
            # Check if user is the customer (appointment.partner_id)
            if appointment.partner_id and appointment.partner_id.id == current_partner.id:
                has_access = True
            else:
                # Check if assigned to current partner (for partners)
                if appointment.assigned_partner_id and appointment.assigned_partner_id.id == current_partner.id:
                    has_access = True
                else:
                    # Check if zip code matches partner's assigned zip codes
                    if appointment.zip_code:
                        PartnerZipCode = request.env['laundry.partner.zip.code'].sudo()
                        partner_zip_assignments = PartnerZipCode.search([
                            ('user_id', '=', current_user.id)
                        ])
                        
                        partner_zip_codes = set()
                        for assignment in partner_zip_assignments:
                            for zip_code_line in assignment.zip_code_line_ids:
                                if zip_code_line.description:
                                    partner_zip_codes.add(zip_code_line.description.strip())
                        
                        if appointment.zip_code.strip() in partner_zip_codes:
                            has_access = True
            
            if not has_access:
                _logger.warning(f"Access denied for user {current_user.id} to image {attachment_id} (appointment {appointment.id})")
                return request.make_response('Access denied', status=403)
            
            # Return the image
            if attachment.datas:
                image_data = base64.b64decode(attachment.datas)
                return request.make_response(
                    image_data,
                    headers=[
                        ('Content-Type', attachment.mimetype or 'image/jpeg'),
                        ('Content-Disposition', f'inline; filename="{attachment.name}"'),
                        ('Cache-Control', 'public, max-age=3600')
                    ]
                )
            else:
                return request.make_response('Image data not found', status=404)
                
        except Exception as e:
            _logger.error(f"Error serving image {attachment_id}: {str(e)}")
            return request.make_response('Error serving image', status=500)

    def _prepare_portal_layout_values(self):
        """Override to add assigned zip codes to portal context"""
        values = super(PartnerController, self)._prepare_portal_layout_values()
        
        # Get assigned zip codes for current user
        current_user = request.env.user
        PartnerZipCode = request.env['laundry.partner.zip.code'].sudo()
        
        # Find all zip code assignments for this user
        partner_zip_assignments = PartnerZipCode.search([
            ('user_id', '=', current_user.id)
        ])
        
        # Collect all unique zip codes
        assigned_zip_codes = []
        zip_code_ids_seen = set()
        
        for assignment in partner_zip_assignments:
            for zip_code_line in assignment.zip_code_line_ids:
                if zip_code_line.id not in zip_code_ids_seen and zip_code_line.description:
                    assigned_zip_codes.append({
                        'id': zip_code_line.id,
                        'code': zip_code_line.description
                    })
                    zip_code_ids_seen.add(zip_code_line.id)
        
        values['assigned_zip_codes'] = assigned_zip_codes
        return values

    def _get_assigned_zip_codes(self):
        """Get assigned zip codes for current user"""
        current_user = request.env.user
        PartnerZipCode = request.env['laundry.partner.zip.code'].sudo()
        
        # Find all zip code assignments for this user
        partner_zip_assignments = PartnerZipCode.search([
            ('user_id', '=', current_user.id)
        ])
        
        # Collect all unique zip codes
        assigned_zip_codes = []
        zip_code_ids_seen = set()
        
        for assignment in partner_zip_assignments:
            for zip_code_line in assignment.zip_code_line_ids:
                if zip_code_line.id not in zip_code_ids_seen and zip_code_line.description:
                    assigned_zip_codes.append({
                        'id': zip_code_line.id,
                        'code': zip_code_line.description
                    })
                    zip_code_ids_seen.add(zip_code_line.id)
        
        return assigned_zip_codes

    def portal_my_details(self, redirect=None, **kw):
        """Override portal account page to include assigned zip codes"""
        response = super(PartnerController, self).portal_my_details(redirect=redirect, **kw)
        
        # Get assigned zip codes
        assigned_zip_codes = self._get_assigned_zip_codes()
        
        # Add to response context if it's a QWeb response
        if hasattr(response, 'qcontext'):
            response.qcontext['assigned_zip_codes'] = assigned_zip_codes
        
        return response


