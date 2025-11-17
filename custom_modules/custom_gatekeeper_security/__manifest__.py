# -*- coding: utf-8 -*-
{
    'name': 'Gatekeeper security management',
    'version': '1.0.0',
    'summary': "End-to-end workflow for field service, estimates, deposits, and customer communication.",
    'category': 'Website/Portal',
    'author': 'TechCog Pvt Ltd',
    'license': 'LGPL-3',
    'depends': [
        'portal','website','contacts','mail','product','sale', 'industry_fsm', 'sms', 'sms_twilio',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/customer_backend_form.xml',
        'views/customer_portal_form.xml',
        'views/customer_portal_card.xml',
        'views/sale_order_views.xml',
        'views/work_order.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_gatekeeper_security/static/src/js/service_request.js',
        ],
        'portal.assets_frontend': [
            'custom_gatekeeper_security/static/src/js/service_request.js',
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
