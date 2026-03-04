# -*- coding: utf-8 -*-
{
    'name': "custom_invoice_sequence",

    'summary': "Custom invoice numbering sequence for accounting",

    'description': """
This module allows you to define and manage custom invoice sequences 
in Odoo, independent of the default journal settings. 
It is useful for creating specialized numbering formats for invoices.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories help filter modules in the apps listing
    # See: https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    'category': 'Accounting',
    'version': '0.1',

    # Dependencies: other modules required for this one to work
    'depends': ['base', 'account'],

    # Data files loaded always
    'data': [
        # Security access rules (uncomment and create if needed)
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],

    # Demo data, only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    # License of the module
    'license': 'LGPL-3',
}
