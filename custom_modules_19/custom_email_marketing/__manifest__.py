{
    'name': 'Custom Email Marketing (Branch Filter)',
    'version': '19.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Filter Mass Mailing contacts and lists by company/branch',
    'description': """
        Extends mass_mailing module to filter mailing lists and contacts
        based on the currently selected company/branch.
    """,
    'author': 'Custom',
    'depends': ['mass_mailing', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'views/mailing_list_views.xml',
        'views/mailing_contact_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
