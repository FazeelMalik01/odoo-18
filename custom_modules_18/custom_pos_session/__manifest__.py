# -*- coding: utf-8 -*-
{
    'name': 'Custom POS Session Report',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Custom POS Session Sales Details Report with Store Name and Auto Download',
    'description': """
        This module customizes the POS session sales details report to display
        the POS store name (config_id) in the report header and automatically
        downloads the daily sales report when closing the POS session.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['point_of_sale'],
    'data': [
        'views/views.xml'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_session/static/src/js/closing_popup.js',
        ],
    },

    'installable': True,
    'auto_install': False,
    'application': False,
}