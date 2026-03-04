{
    'name': "Custom Field Service",

    'summary': "Field Service Customization with Quality Check",

    'description': """
Field Service Customization
============================
This module extends the Field Service functionality by adding:
- Quality Check notebook page to project tasks
- Quality check fields including description, images, optical power values, and DNS settings
- Automatic field service task creation when a helpdesk ticket is created
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Services/Field Service',
    'version': '0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'project', 'helpdesk', 'helpdesk_fsm'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/helpdesk_pdf.xml',
        'views/crm_lead_form.xml',
        'views/contact_menu.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_field_service/static/src/js/cog_menu_patch.js',
        ],
    },
}

