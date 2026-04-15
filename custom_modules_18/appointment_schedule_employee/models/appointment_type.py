# -*- coding: utf-8 -*-
from odoo import models, fields


class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    # Override staff_user_ids to include portal users
    staff_user_ids = fields.Many2many(
        'res.users',
        'appointment_type_res_users_rel',
        # Allow both portal and internal users
        domain="[('share', 'in', [True, False])]",
        string="Users", 
        default=lambda self: self.env.user,
        compute="_compute_staff_user_ids", 
        store=True, 
        readonly=False, 
        tracking=True,
        help="Select users (including portal users) available for this appointment"
    )

    
