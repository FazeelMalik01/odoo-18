{
    'name': "Custom FreedomFun USA",

    'summary': "Webflow webhook integration to create CRM leads",

    'description': """
Receives Webflow form submissions via webhook
and automatically creates CRM leads in Odoo.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Sales/CRM',
    'version': '1.0',

    'depends': [
        'base',
        'crm',
        'product',
        'sale',
        'sale_crm',
    ],

    'data': [
        # 'security/ir.model.access.csv',
        'views/crm_lead_form.xml',
        'data/cron.xml'
    ],

    'demo': [],
    'assets': {
        'web.assets_backend': [
            'custom_freedomfun_usa/static/src/js/index.js',
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
