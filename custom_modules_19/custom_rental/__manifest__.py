{
    'name': "custom_rental",

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
    'version': '0.1.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_renting','web', 'custom_freedomfun_usa'],


    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/res_partner_views.xml',
        'views/rental_zipcode_views.xml',
        'views/sale_order_line_views.xml',
        'views/templates.xml',
        'views/pos_view.xml',
        'views/invoice_pay_template.xml'
    ],

    'assets': {
        'web.assets_backend': [
            'custom_rental/static/src/css/form_view.css',
            "custom_rental/static/src/xml/pos_view.xml",
            "custom_rental/static/src/js/pos_renderer.js",
            "custom_rental/static/src/js/pos_view.js",
            
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

