# -*- coding: utf-8 -*-
{
    'name': 'Appointment Portal Users Support',
    "version": '18.0.1.0.0',
    'summary': 'Allow portal users to be selected as staff for appointments',
    'description': """
        This module extends appointment functionality to allow portal users 
        to be selected as staff members for appointments.
        
        Key Changes:
        - Removes domain restriction that prevented portal users from being selected
        - Portal users now appear in the existing staff_user_ids field
        - No additional UI changes required
    """,
    'category': 'Appointments',
    'author': "Muhammad Faizan",
    'website': "",
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'depends': ['appointment','hr'],
    'data': [
        'views/appointment_type_views.xml',
        'views/portal_user_employee.xml',
    ],
    'installable': True,
    'application': False,
}
