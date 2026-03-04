# -*- coding: utf-8 -*-
{
    'name': "falcon_invoice_report",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Fazeel Malik",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'purchase'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/custom_header.xml',
        'views/custom_footer.xml',
        'views/report_action.xml',
        'views/report.xml',
        'views/hide_action.xml'
    ],
    # only loaded in demonstration mode
    'demo': [],
}



