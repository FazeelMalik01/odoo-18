# -*- coding: utf-8 -*-
{
    "name": "Custom Authorize.Net Payment Gateway",
    "summary": "Authorize.Net payment gateway integration for Odoo",
    "description": """
Custom integration of Authorize.Net payment gateway.
Supports sandbox and production environments,
authorization and capture transactions,
and secure credential configuration.
    """,
    "author": "Your Company Name",
    "website": "https://yourcompany.com",
    "category": "Accounting/Payment Providers",
    "version": "1.0.0",
    "license": "LGPL-3",

    "depends": [
        "base",
        "payment",
        "payment_authorize",
        "website",
    ],

    "data": [
        "views/payment_transaction_views.xml",
    ],

    "installable": True,
    "application": False,
    "auto_install": False,
}
