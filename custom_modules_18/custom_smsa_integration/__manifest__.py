# -*- coding: utf-8 -*-
{
    'name': "SMSA Shipping Integration",
    'summary': "Integrate Odoo with SMSA Express to create and track B2C shipments",

    'description': """
SMSA Express Integration
========================
This module integrates Odoo with SMSA Express APIs.

Features:
- Create B2C shipments directly from Odoo
- Send shipment data to SMSA via API
- Store AWB / tracking numbers
- Support for COD, weight, and address mapping
- Future-ready for tracking and label generation
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Inventory/Delivery',
    'version': '1.0.1',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'sale',
        'stock',
        'delivery',
        'stock_delivery',
        'website_sale',
    ],

    'data': [
        #'security/ir.model.access.csv',
        'data/deliver_carrier_data.xml',
        'views/views.xml',
        'views/res_partner_views.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_picking_views.xml',
        'views/templates.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
