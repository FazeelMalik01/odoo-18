# -*- coding: utf-8 -*-
{
    'name': "custom_purchase",
    'summary': "Falcon Purchase Request for Purchase Orders",
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
     'depends': ['purchase', 'hr'],
     'license': 'LGPL-3',
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/quotation.xml',
        'views/purchase_order.xml',
        'views/delivery_note.xml',
        'views/rfq.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'auto_install': False,
}

