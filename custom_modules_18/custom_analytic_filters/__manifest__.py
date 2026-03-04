# -*- coding: utf-8 -*-
{
    'name': "Custom Analytic Filters",
    'summary': "Enhances Analytic Accounts with PO user lines and customizations",
    'description': """
This module extends Odoo Accounting by:
- Modifying the Analytic Account form view.
- Changing the label of the existing 'name' field.
- Adding a new tab with One2many lines where users can add custom PO text entries.
Each Analytic Account has its own unique PO lines.
    """,
    'author': "Your Company Name",
    'website': "https://www.yourcompany.com",

    'category': 'Accounting/Analytic',
    'version': '1.0',
    'license': 'LGPL-3',

    # ✅ Correct dependency: full Accounting + Base
    'depends': ['base', 'account', 'analytic'],

    # ✅ Data files
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/accounts_menu.xml'
    ],
    'assets': {
    'web.assets_backend': [
        'custom_analytic_filters/static/src/js/account_report_filters.js',
        'custom_analytic_filters/static/src/xml/filter_journal_inherit.xml',
    ],
},


    # Optional demo data
    'demo': [],
}
