# -*- coding: utf-8 -*-
{
    'name': "Website WhatsApp Abandoned Cart",
    'summary': "Send WhatsApp messages for abandoned website carts",

    'description': """
Adds WhatsApp automation for abandoned website carts.
Allows configuration from Website Settings including delay timing.
    """,

    'author': "Tech Cogg",
    'website': "https://yourdomain.com",

    'category': 'Website',
    'version': '18.0.1.0.0',  # adjust version to your Odoo version

    'license': 'LGPL-3',

    'depends': [
        'website',
        'website_sale',
        'sale_management',
        'mail',
    ],

    'data': [
        # 'security/ir.model.access.csv',  # add if needed
        'views/res_config_settings_view.xml',
        'data/cron.xml'
    ],

    'installable': True,
    'application': False,
}