# -*- coding: utf-8 -*-
{
    'name': "custom_pos_receipt",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'point_of_sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'reports/pos_order_report.xml',
        'reports/pos_order_report_doha.xml'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_receipt/static/src/js/receipt_screen.js',
            'custom_pos_receipt/static/src/xml/receipt_screen_extension.xml',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

