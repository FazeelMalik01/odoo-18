from odoo import models, fields, api


class LaundryAppointmentUserResponse(models.Model):
    _name = 'laundry.appointment.user.response'
    _description = 'Laundry Appointment User Response'
    _order = 'create_date desc'

    appointment_id = fields.Many2one(
        'laundry.appointment',
        string='Appointment',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user
    )
    
    status = fields.Selection([
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ], string='Status', required=True, default='accepted')

