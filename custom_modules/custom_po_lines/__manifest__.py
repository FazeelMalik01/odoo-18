# -*- coding: utf-8 -*-
{
    'name': 'Custom Purchase Order Lines',
    'version': '18.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Add barcode field to purchase order lines',
    'description': """
        This module adds a barcode field to purchase order lines.
        The barcode field is displayed before the product name in the purchase order line views.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_line_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}