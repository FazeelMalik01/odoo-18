# -*- coding: utf-8 -*-
{
    'name': "Custom POS Card",

    'summary': "Capture last 4 digits of card number in POS payments",

    'description': """
        This module adds a card number input field (last 4 digits) to the POS payment screen
        when the Card payment method is selected. The captured value is stored in the
        pos.payment model and displayed in the backend order form.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Point of Sale',
    'version': '18.0.1.0.0',

    'depends': ['point_of_sale'],

    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],

    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_card/static/src/**/*',
        ],
    },

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
