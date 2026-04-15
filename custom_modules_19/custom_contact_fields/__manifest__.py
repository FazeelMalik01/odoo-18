{
    'name': "custom_contact_fields",

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
    'version': '0.4',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'l10n_ca', 'sale', 'sale_stock', 'account', 'product_expiry', 'custom_dealers_portal'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/contact_type_data.xml',
        'views/views.xml',
        'views/contact_type_views.xml',
        'views/sale_order_ext_views.xml',
        'views/purchase_order_ext_views.xml',
        'views/product_fields.xml',
        'views/sale_report_ext.xml',
        'views/account_invoice_report_ext.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_contact_fields/static/src/js/contact_form.js',
            'custom_contact_fields/static/src/css/contact_types.css',
        ],
    },
}

