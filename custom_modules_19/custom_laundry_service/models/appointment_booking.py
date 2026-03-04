from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LaundryAppointmentBooking(models.Model):
    _name = 'laundry.appointment.booking'
    _description = 'Laundry Appointment Slot Booking'
    _order = 'booking_date desc, id desc'

    appointment_id = fields.Many2one(
        'laundry.appointment', 
        string='Appointment', 
        required=True, 
        ondelete='cascade',
        index=True
    )
    slot_id = fields.Many2one(
        'appointment.slot', 
        string='Time Slot', 
        required=True,
        index=True
    )
    hour_offset = fields.Integer(
        string='Hour Offset',
        default=0,
        help='Which hour within the slot range (0 = first hour, 1 = second hour, etc.)'
    )
    booking_date = fields.Date(
        string='Booking Date', 
        required=True,
        index=True,
        help='The specific date for which this slot is booked'
    )
    status = fields.Selection([
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='active', required=True)
    
    # Related fields for easier access
    customer_name = fields.Char(related='appointment_id.customer_name', string='Customer', store=True)
    partner_id = fields.Many2one(related='appointment_id.partner_id', string='Partner', store=True)
    
    # Removed SQL constraint - we now check partner availability instead
    
    @api.constrains('slot_id', 'hour_offset', 'booking_date', 'status')
    def _check_slot_availability(self):
        """Check if slot is available based on partner availability for the zip code"""
        for record in self:
            if record.status == 'active':
                # Get the appointment's zip code
                appointment = record.appointment_id
                if not appointment:
                    continue
                
                zip_code = appointment.zip_code
                
                # If no zip code, use old behavior - block if any booking exists
                if not zip_code:
                    existing = self.search([
                        ('slot_id', '=', record.slot_id.id),
                        ('hour_offset', '=', record.hour_offset),
                        ('booking_date', '=', record.booking_date),
                        ('status', '=', 'active'),
                        ('id', '!=', record.id)
                    ], limit=1)
                    if existing:
                        raise ValidationError(
                            f'This time slot is already booked by {existing.customer_name} '
                            f'for {record.booking_date}. Please select a different time slot.'
                        )
                    continue
                
                zip_code = zip_code.strip()
                
                # Get all partners with matching zip codes
                PartnerZipCode = self.env['laundry.partner.zip.code'].sudo()
                partner_zip_assignments = PartnerZipCode.search([])
                
                partner_ids = []
                for assignment in partner_zip_assignments:
                    for zip_code_line in assignment.zip_code_line_ids:
                        if zip_code_line.description and zip_code_line.description.strip() == zip_code:
                            if assignment.user_id and assignment.user_id.partner_id:
                                partner_ids.append(assignment.user_id.partner_id.id)
                                break
                
                # If partners found for this zip code, check partner availability
                if partner_ids:
                    # Get all existing bookings for this slot+date
                    existing_bookings = self.search([
                        ('slot_id', '=', record.slot_id.id),
                        ('hour_offset', '=', record.hour_offset),
                        ('booking_date', '=', record.booking_date),
                        ('status', '=', 'active'),
                        ('id', '!=', record.id)
                    ])
                    
                    # Get partners who have confirmed bookings (assigned_partner_id is set)
                    booked_partner_ids = set()
                    for booking in existing_bookings:
                        if booking.appointment_id and booking.appointment_id.assigned_partner_id:
                            booked_partner_ids.add(booking.appointment_id.assigned_partner_id.id)
                    
                    # Check if ALL partners are booked
                    partner_ids_set = set(partner_ids)
                    if booked_partner_ids.issuperset(partner_ids_set):
                        # All partners are booked, block this booking
                        raise ValidationError(
                            f'This time slot is fully booked for zip code {zip_code} on {record.booking_date}. '
                            f'All available partners are already assigned. Please select a different time slot.'
                        )
                    # If not all partners are booked, allow the booking
                else:
                    # No partners found for zip code, use old behavior - block if any booking exists
                    existing = self.search([
                        ('slot_id', '=', record.slot_id.id),
                        ('hour_offset', '=', record.hour_offset),
                        ('booking_date', '=', record.booking_date),
                        ('status', '=', 'active'),
                        ('id', '!=', record.id)
                    ], limit=1)
                    if existing:
                        raise ValidationError(
                            f'This time slot is already booked by {existing.customer_name} '
                            f'for {record.booking_date}. Please select a different time slot.'
                        )
    
    def name_get(self):
        """Custom display name"""
        result = []
        for record in self:
            name = f"{record.booking_date} - {record.slot_id.display_name}"
            result.append((record.id, name))
        return result
