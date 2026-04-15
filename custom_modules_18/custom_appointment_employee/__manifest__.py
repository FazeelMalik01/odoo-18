{
    'name': 'Custom Appointment Employee',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Change staff_ids to link with hr.employee in appointment.type',
    'depends': ['appointment', 'hr','sale'],
    'data': [
        'views/appointment_type_views.xml',
        'views/template_web_url_access.xml',
    ],
    'installable': True,
    'auto_install': False,
}
