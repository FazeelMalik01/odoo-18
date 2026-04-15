# -*- coding: utf-8 -*-
{
    "name": "IPOS Pay",
    "version": "19.0.1.0.6",
    "category": "Accounting/Payment Providers",
    "summary": "Custom IPOS Payment Provider for Odoo 19",
    "description": """
IPOS Pay - Custom Payment Provider
====================================
Integrates IPOS payment gateway as an Odoo payment provider.

Features:
- Merchant ID (TPN) configuration
- Auth Token configuration (no token generation API)
- Separate Test and Live base URL configuration
- Easy toggle between Test and Live modes
    """,
    "author": "Custom",
    "depends": ["payment", "account_payment", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/payment_provider_template.xml",
        "data/payment_provider_data.xml",
        "data/payment_provider_module_link.xml",
        "views/payment_provider_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "custom_ipos_pay/static/src/interactions/payment_form.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
}
