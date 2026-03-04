{
    'name': "Custom Accounts Tax Mapping",
    'version': '1.0.0',
    'summary': "Adds custom tax mapping lines to fiscal positions for advanced tax configuration",
    'description': """
Custom Accounts Tax Mapping Module for Odoo 19.

This module extends the standard Accounting Fiscal Position feature
by allowing custom tax mapping lines. You can define which tax
replaces another tax under specific fiscal positions, making tax
management flexible for sales and purchase scenarios.

Features:
- Extend fiscal positions with custom tax mapping lines
- Map source taxes to destination taxes
- Compatible with Odoo 19 Accounting and Invoicing
""",
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'license': 'LGPL-3',  # Proper Odoo license key
    'category': 'Accounting/Tax',
    'sequence': 10,
    'depends': ['base', 'account', 'sale'],  # dependencies
    'data': [
        'security/ir.model.access.csv',  # model access
        'views/views.xml',               # form/list views
        'views/templates.xml',           # optional templates
    ],
    'demo': [
        'demo/demo.xml',
    ],
}