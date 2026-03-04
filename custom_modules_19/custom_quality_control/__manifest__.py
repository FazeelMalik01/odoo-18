{
    'name': "Custom Quality Control",

    'summary': "Custom enhancements for Quality Control module with Helpdesk integration",

    'description': """
Custom Quality Control Module
=============================
This module extends the standard Quality Control functionality with:
    
    * Custom quality check submission workflow
    * Multiple images support for quality checks
    * Custom quality manager group with restricted button access
    * Automated Field Service task creation from Helpdesk tickets
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Supply Chain/Quality',
    'version': '0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'quality', 'quality_control', 'project', 'helpdesk_fsm'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/custom_worksheet_views.xml',
        'views/quality_check_views.xml',
        'views/quality_check_wizard_views.xml',
        'views/views.xml',
        'views/templates.xml',
        'data/menu_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    
    # License
    'license': 'LGPL-3',
    
    # Application
    'application': False,
    'installable': True,
    'auto_install': False,
}

