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
    "depends": ["base", "point_of_sale", "account"],

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
            "custom_pos_discount/static/src/js/orderline_tax_label.js",
            "custom_pos_discount/static/src/js/orderline_format.js",
            "custom_pos_discount/static/src/js/order_widget.js",
            "custom_pos_discount/static/src/js/partner_list.js",
            "custom_pos_discount/static/src/xml/discount_button.xml",
            "custom_pos_discount/static/src/xml/orderline_ui.xml",
            "custom_pos_discount/static/src/xml/receipt_template.xml",
            'custom_pos_discount/static/src/js/numpad.js',
        ],
    },

    # Demo data
    "demo": [
        "demo/demo.xml",
    ],

    "license": "LGPL-3",
}
