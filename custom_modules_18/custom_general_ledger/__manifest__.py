# -*- coding: utf-8 -*-
{
    "name": "custom_general_ledger",
    "summary": "Custom General Ledger",
    "description": """
    provides an interactive and dynamic general ledger report
    """,
    "author": "My Company",
    "website": "https://www.yourcompany.com",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Uncategorized",
    "version": "0.1",
    # any module necessary for this one to work correctly
    "depends": ["base", "sale", "accountant", "account", "project"],
    # always loaded
    "data": [
        # 'security/ir.model.access.csv',
        "views/menus.xml",
        "views/views.xml",
        "views/templates.xml",

    ],
    "assets": {
        "web.assets_backend": [
            "custom_general_ledger/static/src/js/general_ledger.js",
            'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js',
            "custom_general_ledger/static/src/xml/general_ledger.xml",
        ],
    },
    # only loaded in demonstration mode
    "demo": [
        "demo/demo.xml",
    ],
}
