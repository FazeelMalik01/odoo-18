# -*- coding: utf-8 -*-
{
    'name': "Custom Progress Report",

    'summary': "Daily progress reporting form for project tasks via portal",

    'description': """
This module allows portal users to submit daily progress reports related to 
project tasks. The reports are visible in the portal and linked to corresponding 
tasks in the backend for review and tracking.
    """,

    'author': "Fazeel Malik",
    'website': "https://www.yourcompany.com",
    'license': "LGPL-3",

    'category': 'Project',
    'version': '1.0',

    # Dependencies
    'depends': [
        'base',
        'project',
        'portal',
        'mail',
        'website',   # if portal form is shown on website
    ],

    # Data files loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'views/progress_report_card.xml',
        'views/progress_list_view.xml',
        'views/project_task.xml',
        'views/task_view.xml',
        'views/task_list_view.xml'
    ],

    # Demo data
    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
