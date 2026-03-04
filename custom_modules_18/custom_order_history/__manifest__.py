# -*- coding: utf-8 -*-
{
    'name': "Custom Order History",
    'summary': "Filter POS order history by specific customer ID instead of name",
    'description': """
        Custom Order History Module
        ===========================
        
        This module fixes the issue where clicking on a customer's "All Orders" 
        shows orders from all customers with the same name, instead of only 
        showing orders for that specific customer.
        
        Features:
        - Filters orders by customer ID instead of customer name
        - Ensures accurate order history for customers with duplicate names
        - Works with the POS ticket screen order history
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Point of Sale',
    'version': '0.1.0',
    'depends': ['point_of_sale'],
    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_order_history/static/src/js/partner_list.js',
            'custom_order_history/static/src/js/ticket_screen.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

