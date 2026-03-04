# -*- coding: utf-8 -*-
{
    'name': 'Gatekeeper security management',
    'version': '1.0.0',
    'summary': "End-to-end workflow for field service, estimates, deposits, and customer communication.",
    'category': 'Website/Portal',
    'author': 'TechCog Pvt Ltd',
    'license': 'LGPL-3',
    'depends': [
        'portal','website','contacts','mail','product','sale', 'industry_fsm', 'sms', 'sms_twilio', 'account',
    ],
    'data': [
        'security/technician_groups.xml',
        'security/technician_security_rules.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/customer_backend_form.xml',
        'views/customer_portal_form.xml',
        'views/customer_portal_card.xml',
        'views/technician_portal_card.xml',
        'views/technician_portal_templates.xml',
        'views/project_task_views.xml',
        'views/sale_order_views.xml',
        'views/work_worksheet_views.xml',
        'views/work_order.xml',
        'views/invoice_workorder_button.xml',
        'views/work_order_portal_form.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_gatekeeper_security/static/src/js/service_request.js',
            'custom_gatekeeper_security/static/src/js/timer.js',
        ],
        'portal.assets_frontend': [
            'custom_gatekeeper_security/static/src/js/service_request.js',
            'custom_gatekeeper_security/static/src/js/timer.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [
        'custom_gatekeeper_security/static/src/img/service-request.svg',
    ],
    'icon': 'custom_gatekeeper_security/static/src/img/service-request.svg',
}
