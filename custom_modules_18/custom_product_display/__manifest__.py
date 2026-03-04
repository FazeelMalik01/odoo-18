# -*- coding: utf-8 -*-
{
    'name': "custom_product_display",

    'summary': "Hide out-of-stock products and empty categories from website shop",

    'description': """
Custom Product Display Module
=============================
This module hides out-of-stock products and empty categories from the website shop:
- Products with 0 on-hand quantity are not displayed
- Categories containing only out-of-stock products are hidden
- Subcategories with only out-of-stock products are also hidden
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website_sale', 'stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/website_sale_templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

