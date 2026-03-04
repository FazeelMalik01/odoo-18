# -*- coding: utf-8 -*-
{
    "name": "custom_pos_price",
    "summary": "Short (1 phrase/line) summary of the module's purpose",
    "description": """
Long description of module's purpose
    """,
    "author": "My Company",
    "website": "https://www.yourcompany.com",
    "category": "Uncategorized",
    "version": "0.1",
    "depends": ["base", "point_of_sale", 'sale', 'stock'],
    "data": [
        # 'security/ir.model.access.csv',
        "views/views.xml",
        "views/templates.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "custom_pos_price/static/src/js/pos_store_patch.js",
        ],
    },
    "demo": [
        "demo/demo.xml",
    ],
}
