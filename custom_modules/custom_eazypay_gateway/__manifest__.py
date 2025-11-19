# -*- coding: utf-8 -*-
{
    'name': "EazyPay Payment Gateway",
    'summary': "EazyPay Payment Gateway Integration for Odoo",
    'description': """
        EazyPay Payment Gateway Integration
        ===================================
        
        This module integrates EazyPay payment gateway with Odoo, allowing customers
        to pay using EazyPay during checkout on the website.
        
        Features:
        - Support for multiple payment methods (Benefit Gateway, Credit Card, Apple Pay)
        - Secure payment processing with HMAC-SHA256 authentication
        - Webhook support for payment status updates
        - Automatic payment status synchronization
        
        Configuration:
        1. Go to Accounting > Configuration > Payment Providers
        2. Create or edit an EazyPay provider
        3. Enter your App ID and Secret Key
        4. Configure payment methods
        5. Enable the provider
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Accounting/Payment',
    'version': '1.0',
    'depends': ['payment', 'website'],
    'data': [
        'views/payment_eazypay_templates.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',  # Depends on payment_eazypay_templates.xml and payment_method_data.xml
        'views/payment_provider_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_eazypay_gateway/static/src/css/payment_method_image.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
