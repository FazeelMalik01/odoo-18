{
    "name": "Custom POS Discount",
    "summary": "Add custom discount feature in POS",
    "description": """
Custom POS Discount
====================
This module provides additional discount functionality in Point of Sale.
    """,
    "author": "TechCog",
    "website": "https://www.yourcompany.com",
    "category": "Point of Sale",
    "version": "0.1",

    # Dependencies
    "depends": ["base", "point_of_sale"],

    # Data files loaded always
    "data": [
        # "security/ir.model.access.csv",
        "views/views.xml",
        "views/templates.xml",
    ],

    # Assets for POS
    "assets": {
        "point_of_sale._assets_pos": [
            "custom_pos_discount/static/src/js/discount.js",
            "custom_pos_discount/static/src/xml/discount_button.xml",
            "custom_pos_discount/static/src/xml/orderline_ui.xml",
            "custom_pos_discount/static/src/xml/receipt_template.xml",
        ],
    },

    # Demo data
    "demo": [
        "demo/demo.xml",
    ],

    "license": "LGPL-3",
}
