# -*- coding: utf-8 -*-
{
    'name': "Website Bahrain Address Customization",

    'summary': "Customize website address fields specifically for Bahrain",

    'description': """
This module customizes the website address form for Bahrain:

- Removes Address Line 1 and Address Line 2 fields
- Adds Bahrain-specific fields:
    * Flat (Optional)
    * Building (Mandatory)
    * Road (Mandatory)
    * Block (Mandatory)
- Applies changes only when country is set to Bahrain
- Enhances user experience by aligning address format with Bahrain standards
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Website',
    'version': '1.0',

    'depends': [
        'base',
        'website',
        'website_sale',   # if used in checkout
    ],

    'data': [
        # 'security/ir.model.access.csv',  # if models are added

    ],

    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}