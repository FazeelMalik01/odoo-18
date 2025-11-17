# -*- coding: utf-8 -*-
{
    'name': 'Custom POS Loyalty Expiry',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Custom loyalty program expiry functionality for Point of Sale',
    'description': """
        Custom POS Loyalty Expiry
        =========================
        
        This module extends the Point of Sale loyalty functionality to handle
        loyalty program expiry dates and related features.
        
        Features:
        ---------
        * Manage loyalty program expiry dates
        * Track and validate loyalty points expiration
        * Custom expiry rules for POS loyalty programs
    """,
    'author': 'TechCog',
    'website': 'https://www.techcog.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'point_of_sale',
        'loyalty',
    ],
    'data': [
        #'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "custom_pos_loyalty_expiry/static/src/js/loyalty_return_patch.js",
        ],
    },
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
