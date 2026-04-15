{
    'name': "Custom Dealers Portal",

    'summary': "Custom portal interface for dealers to access and manage their information",

    'description': """
Custom Dealers Portal
=====================
This module provides a customized portal interface for dealers, allowing them to:
- Access their dealer-specific information through the portal
- View and manage dealer-related data
- Interact with dealer-specific features and workflows
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/19.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales/Portal',
    'version': '0.4',
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,

    # any module necessary for this one to work correctly
    # crm is required so dealer signups can automatically create a lead
    'depends': ['base', 'portal', 'website', 'sale', 'web', 'website_sale', 'crm'],

    # always loaded
    'data': [
        'security/dealer_groups.xml',
        'views/dealers_portal_card.xml',
        'views/dealers_portal_list.xml',
        'views/res_partner.xml',
        'views/purchase_order_card.xml',
        'views/purchase_order_list.xml',
        'views/purchase_order_form.xml',
        'views/sale_order_view.xml',
        'views/res_users.xml',
        'views/dealer_signup.xml',
        'views/login_signup_modifications.xml',
        'views/product_catalog.xml',
        'views/portal_pricelist_readonly.xml',
        'views/portal_home_pricelist.xml',
        'views/website_header_customizations.xml',
        'views/website_footer_customizations.xml',
        'views/website_robots_and_portal_meta.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "assets": {
        "web.assets_frontend": [
            "custom_dealers_portal/static/src/css/portal.scss",
            "custom_dealers_portal/static/src/js/add_contacts.js",
        ],
    },
}

