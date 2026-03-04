{
    'name': "custom_laundry_service",

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
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'portal', 'mail', 'product', 'sale', 'appointment', 'auth_signup', 'website'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security_groups.xml',
        'views/views.xml',
        'views/product_template_views.xml',
        'views/service_request_views.xml',
        'views/partner_templates.xml',
        'views/customer_templates.xml',
        'views/zip_code.xml',
        'views/zip_code_portal_templates.xml',
        'views/user_management.xml',
        'views/login_templates.xml',
        'views/pricing_templates.xml',
        'views/partner_reporting_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_laundry_service/static/src/img/**/*',
            'custom_laundry_service/static/src/css/login_form.css',
            'custom_laundry_service/static/src/css/appointment_form.css',
            'custom_laundry_service/static/src/js/appointment_form.js',
            'custom_laundry_service/static/src/js/appointment_time_slots.js',
            'custom_laundry_service/static/src/js/service_requests.js',
            'custom_laundry_service/static/src/js/social_security_format.js',
            'custom_laundry_service/static/src/js/zip_city_filter.js',
            'custom_laundry_service/static/src/js/zip_searchable_select.js',
        ],
    },
    'application': True,
}

